from dataclasses import asdict
from typing import Any
from urllib.parse import unquote_plus

from app.core.config import settings
from app.core.exceptions import AppError
from app.db.session import SessionLocal
from app.services.document_service import DocumentService


class S3EventProcessingError(Exception):
    pass

# This Lambda function is triggered by S3 ObjectCreated events. It processes the
# event to determine which document upload has completed, and then calls the
# DocumentService to finalize the upload process in the application.
def handler(event: dict[str, Any], _context: object) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for record in event.get("Records", []):
        parsed = _parse_record(record)
        if parsed is None:
            results.append({"status": "skipped", "reason": "invalid_record"})
            continue

        bucket, storage_key = parsed
        if bucket != settings.s3_bucket:
            results.append(
                {
                    "bucket": bucket,
                    "storage_key": storage_key,
                    "status": "skipped",
                    "reason": "bucket_mismatch",
                }
            )
            continue
        # Valid record for our bucket, so we attempt to complete the upload.
        try:
            with SessionLocal() as db:
                result = DocumentService(db).complete_upload_by_storage_key(storage_key)
                results.append(
                    {
                        "bucket": bucket,
                        **asdict(result),
                    }
                )
        except AppError as exc:
            failures.append(
                {
                    "bucket": bucket,
                    "storage_key": storage_key,
                    "code": exc.code,
                    "message": exc.message,
                }
            )
        except Exception as exc:
            failures.append(
                {
                    "bucket": bucket,
                    "storage_key": storage_key,
                    "code": exc.__class__.__name__,
                    "message": str(exc),
                }
            )

    summary = {
        "processed": sum(
            1
            for result in results
            if result["status"] in {"uploaded", "already_uploaded", "rejected"}
        ),
        "skipped": sum(1 for result in results if result["status"] == "skipped"),
        "failed": len(failures),
        "results": results,
        "failures": failures,
    }
    if failures:
        raise S3EventProcessingError(summary)
    return summary


def _parse_record(record: dict[str, Any]) -> tuple[str, str] | None:
    event_name = record.get("eventName")
    if event_name is not None and not str(event_name).startswith("ObjectCreated:"):
        return None

    try:
        bucket = record["s3"]["bucket"]["name"]
        raw_key = record["s3"]["object"]["key"]
    except KeyError:
        return None

    return str(bucket), unquote_plus(str(raw_key))
