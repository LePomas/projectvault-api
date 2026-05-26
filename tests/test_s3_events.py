from urllib.parse import quote_plus

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.exceptions import AppError
from app.lambda_handlers import s3_events
from app.models.document import Document
from app.models.project import Project, ProjectMember
from app.models.user import User
from app.services.storage import StoredObjectMetadata


class FakeS3Storage:
    def __init__(self) -> None:
        self.objects: dict[str, StoredObjectMetadata] = {}
        self.deleted_keys: list[str] = []
        self.error_keys: set[str] = set()

    def get_metadata(self, storage_key: str) -> StoredObjectMetadata:
        if storage_key in self.error_keys:
            raise AppError(
                status_code=500,
                code="DOCUMENT_STORAGE_ERROR",
                message="Document could not be read from storage.",
            )
        return self.objects[storage_key]

    def delete(self, storage_key: str) -> None:
        self.deleted_keys.append(storage_key)
        self.objects.pop(storage_key, None)


@pytest.fixture
def lambda_session(db_engine, monkeypatch: pytest.MonkeyPatch) -> sessionmaker:
    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db_engine,
    )
    monkeypatch.setattr(s3_events, "SessionLocal", testing_session_local)
    return testing_session_local


@pytest.fixture
def fake_s3_storage(monkeypatch: pytest.MonkeyPatch) -> FakeS3Storage:
    storage = FakeS3Storage()
    monkeypatch.setattr(
        "app.services.document_service.get_document_storage",
        lambda: storage,
    )
    return storage


@pytest.fixture(autouse=True)
def s3_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "s3_bucket", "projectvault-documents")
    monkeypatch.setattr(settings, "project_storage_limit_bytes", 104_857_600)


def test_s3_event_finalizes_pending_document(
    db_session: Session,
    lambda_session: sessionmaker,
    fake_s3_storage: FakeS3Storage,
) -> None:
    document = create_pending_document(db_session, "projects/1/contract.pdf")
    fake_s3_storage.objects[document.storage_key] = StoredObjectMetadata(
        size_bytes=1234,
        content_type="application/pdf",
    )

    result = s3_events.handler(s3_event(document.storage_key), None)

    assert result["processed"] == 1
    assert result["skipped"] == 0
    assert result["failed"] == 0
    assert result["results"][0]["status"] == "uploaded"

    db_session.expire_all()
    saved_document = db_session.get(Document, document.id)
    saved_project = db_session.get(Project, document.project_id)
    assert saved_document is not None
    assert saved_project is not None
    assert saved_document.status == "uploaded"
    assert saved_document.size_bytes == 1234
    assert saved_document.content_type == "application/pdf"
    assert saved_project.documents_count == 1
    assert saved_project.total_size_bytes == 1234


def test_s3_event_is_idempotent_for_uploaded_document(
    db_session: Session,
    lambda_session: sessionmaker,
    fake_s3_storage: FakeS3Storage,
) -> None:
    document = create_pending_document(
        db_session,
        "projects/1/uploaded.pdf",
        status="uploaded",
        size_bytes=42,
        project_total_size_bytes=42,
        project_documents_count=1,
    )

    result = s3_events.handler(s3_event(document.storage_key), None)

    assert result["processed"] == 1
    assert result["results"][0]["status"] == "already_uploaded"
    assert fake_s3_storage.deleted_keys == []

    db_session.expire_all()
    saved_project = db_session.get(Project, document.project_id)
    assert saved_project is not None
    assert saved_project.documents_count == 1
    assert saved_project.total_size_bytes == 42


def test_s3_event_rejects_over_limit_upload_and_deletes_object(
    db_session: Session,
    lambda_session: sessionmaker,
    fake_s3_storage: FakeS3Storage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "project_storage_limit_bytes", 5)
    document = create_pending_document(db_session, "projects/1/large.pdf")
    fake_s3_storage.objects[document.storage_key] = StoredObjectMetadata(
        size_bytes=6,
        content_type="application/pdf",
    )

    result = s3_events.handler(s3_event(document.storage_key), None)

    assert result["processed"] == 1
    assert result["results"][0]["status"] == "rejected"
    assert result["results"][0]["reason"] == "storage_limit_exceeded"
    assert fake_s3_storage.deleted_keys == [document.storage_key]

    db_session.expire_all()
    saved_document = db_session.get(Document, document.id)
    saved_project = db_session.get(Project, document.project_id)
    assert saved_document is not None
    assert saved_project is not None
    assert saved_document.status == "deleted"
    assert saved_document.deleted_at is not None
    assert saved_project.documents_count == 0
    assert saved_project.total_size_bytes == 0


def test_s3_event_decodes_keys_and_skips_other_buckets(
    db_session: Session,
    lambda_session: sessionmaker,
    fake_s3_storage: FakeS3Storage,
) -> None:
    storage_key = "projects/1/space name.pdf"
    document = create_pending_document(db_session, storage_key)
    fake_s3_storage.objects[storage_key] = StoredObjectMetadata(
        size_bytes=12,
        content_type="application/pdf",
    )
    event = {
        "Records": [
            s3_record(quote_plus(storage_key)),
            s3_record("projects/2/other.pdf", bucket="other-bucket"),
            {"eventName": "ObjectRemoved:Delete"},
            {"eventName": "ObjectCreated:Put"},
        ]
    }

    result = s3_events.handler(event, None)

    assert result["processed"] == 1
    assert result["skipped"] == 3
    assert result["results"][0]["storage_key"] == storage_key
    assert result["results"][1]["reason"] == "bucket_mismatch"
    assert result["results"][2]["reason"] == "invalid_record"
    assert result["results"][3]["reason"] == "invalid_record"

    db_session.expire_all()
    saved_document = db_session.get(Document, document.id)
    assert saved_document is not None
    assert saved_document.status == "uploaded"


def test_s3_event_reports_failures_after_processing_batch(
    db_session: Session,
    lambda_session: sessionmaker,
    fake_s3_storage: FakeS3Storage,
) -> None:
    good = create_pending_document(db_session, "projects/1/good.pdf")
    bad = create_pending_document(
        db_session,
        "projects/1/bad.pdf",
        login="bob",
        email="bob@example.com",
        project_name="Bad Project",
    )
    fake_s3_storage.objects[good.storage_key] = StoredObjectMetadata(
        size_bytes=12,
        content_type="application/pdf",
    )
    fake_s3_storage.error_keys.add(bad.storage_key)

    with pytest.raises(s3_events.S3EventProcessingError) as exc_info:
        s3_events.handler(
            {
                "Records": [
                    s3_record(good.storage_key),
                    s3_record(bad.storage_key),
                ]
            },
            None,
        )

    summary = exc_info.value.args[0]
    assert summary["processed"] == 1
    assert summary["failed"] == 1
    assert summary["failures"][0]["storage_key"] == bad.storage_key
    assert summary["failures"][0]["code"] == "DOCUMENT_STORAGE_ERROR"

    db_session.expire_all()
    saved_good = db_session.get(Document, good.id)
    saved_bad = db_session.get(Document, bad.id)
    assert saved_good is not None
    assert saved_bad is not None
    assert saved_good.status == "uploaded"
    assert saved_bad.status == "pending_upload"


def create_pending_document(
    db: Session,
    storage_key: str,
    *,
    login: str = "owner",
    email: str = "owner@example.com",
    project_name: str = "Project Alpha",
    status: str = "pending_upload",
    size_bytes: int = 0,
    project_total_size_bytes: int = 0,
    project_documents_count: int = 0,
) -> Document:
    user = User(login=login, email=email, password_hash="hash")
    db.add(user)
    db.flush()

    project = Project(
        name=project_name,
        description="Initial description",
        owner_id=user.id,
        total_size_bytes=project_total_size_bytes,
        documents_count=project_documents_count,
    )
    db.add(project)
    db.flush()

    db.add(ProjectMember(project_id=project.id, user_id=user.id, role="owner"))
    document = Document(
        project_id=project.id,
        uploaded_by_id=user.id,
        filename=storage_key.rsplit("/", 1)[-1],
        content_type="application/pdf",
        size_bytes=size_bytes,
        storage_key=storage_key,
        status=status,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def s3_event(storage_key: str, *, bucket: str = "projectvault-documents") -> dict:
    return {"Records": [s3_record(storage_key, bucket=bucket)]}


def s3_record(
    storage_key: str,
    *,
    bucket: str = "projectvault-documents",
) -> dict:
    return {
        "eventName": "ObjectCreated:Put",
        "s3": {
            "bucket": {"name": bucket},
            "object": {"key": storage_key},
        },
    }
