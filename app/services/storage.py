from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from shutil import copyfileobj
from typing import BinaryIO, Protocol
from uuid import uuid4

from app.core.config import settings
from app.core.exceptions import AppError


@dataclass(frozen=True)
class StoredObjectMetadata:
    size_bytes: int
    content_type: str | None


@dataclass(frozen=True)
class PresignedUrl:
    url: str
    expires_in: int
    headers: Mapping[str, str]


class DocumentStorage(Protocol):
    def generate_key(self, project_id: int, filename: str) -> str: ...

    def save(
        self,
        storage_key: str,
        source: BinaryIO,
        content_type: str | None = None,
    ) -> int: ...

    def delete(self, storage_key: str) -> None: ...

    def download_path(self, storage_key: str) -> Path: ...

    def presign_upload(self, storage_key: str, content_type: str) -> PresignedUrl: ...

    def presign_download(self, storage_key: str) -> PresignedUrl: ...

    def get_metadata(self, storage_key: str) -> StoredObjectMetadata: ...


class LocalDocumentStorage:
    def __init__(self, root_path: str | Path | None = None) -> None:
        self.root_path = Path(root_path or settings.document_storage_path)

    def generate_key(self, project_id: int, filename: str) -> str:
        suffix = Path(filename).suffix.lower()
        return str(PurePosixPath("projects", str(project_id), f"{uuid4().hex}{suffix}"))

    def save(
        self,
        storage_key: str,
        source: BinaryIO,
        content_type: str | None = None,
    ) -> int:
        path = self._path_for_key(storage_key)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("wb") as destination:
                copyfileobj(source, destination)
        except OSError as exc:
            raise AppError(
                status_code=500,
                code="DOCUMENT_STORAGE_ERROR",
                message="Document could not be stored.",
            ) from exc
        return path.stat().st_size

    def delete(self, storage_key: str) -> None:
        path = self._path_for_key(storage_key)
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            raise AppError(
                status_code=500,
                code="DOCUMENT_STORAGE_ERROR",
                message="Document could not be deleted from storage.",
            ) from exc

    def download_path(self, storage_key: str) -> Path:
        path = self._path_for_key(storage_key)
        if not path.is_file():
            raise AppError(
                status_code=500,
                code="DOCUMENT_STORAGE_ERROR",
                message="Document could not be read from storage.",
            )
        return path

    def _path_for_key(self, storage_key: str) -> Path:
        key_path = PurePosixPath(storage_key)
        if key_path.is_absolute() or ".." in key_path.parts:
            raise AppError(
                status_code=500,
                code="DOCUMENT_STORAGE_ERROR",
                message="Document storage key is invalid.",
            )
        return self.root_path.joinpath(*key_path.parts)

    def presign_upload(self, storage_key: str, content_type: str) -> PresignedUrl:
        raise AppError(
            status_code=500,
            code="DOCUMENT_STORAGE_ERROR",
            message="Presigned uploads require S3-compatible storage.",
        )

    def presign_download(self, storage_key: str) -> PresignedUrl:
        raise AppError(
            status_code=500,
            code="DOCUMENT_STORAGE_ERROR",
            message="Presigned downloads require S3-compatible storage.",
        )

    def get_metadata(self, storage_key: str) -> StoredObjectMetadata:
        path = self.download_path(storage_key)
        return StoredObjectMetadata(
            size_bytes=path.stat().st_size,
            content_type=None,
        )


class S3DocumentStorage:
    def __init__(
        self,
        *,
        bucket: str | None = None,
        endpoint_url: str | None = None,
        public_endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        region: str | None = None,
        expires_in: int | None = None,
        client: object | None = None,
        presign_client: object | None = None,
    ) -> None:
        self.bucket = bucket or settings.s3_bucket
        self.endpoint_url = endpoint_url or settings.s3_endpoint_url
        self.public_endpoint_url = (
            public_endpoint_url
            if public_endpoint_url is not None
            else settings.s3_public_endpoint_url
        )
        self.expires_in = expires_in or settings.s3_presigned_url_expires_seconds
        access_key = access_key or settings.s3_access_key
        secret_key = secret_key or settings.s3_secret_key
        region = region or settings.s3_region
        self.client = client or self._create_client(
            endpoint_url=self.endpoint_url,
            access_key=access_key,
            secret_key=secret_key,
            region=region,
        )
        presign_endpoint_url = self.public_endpoint_url or self.endpoint_url
        self.presign_client = presign_client or (
            self.client
            if client is not None or presign_endpoint_url == self.endpoint_url
            else self._create_client(
                endpoint_url=presign_endpoint_url,
                access_key=access_key,
                secret_key=secret_key,
                region=region,
            )
        )

    def generate_key(self, project_id: int, filename: str) -> str:
        suffix = Path(filename).suffix.lower()
        return str(PurePosixPath("projects", str(project_id), f"{uuid4().hex}{suffix}"))

    def save(
        self,
        storage_key: str,
        source: BinaryIO,
        content_type: str | None = None,
    ) -> int:
        size_bytes = self._source_size(source)
        params = {
            "Bucket": self.bucket,
            "Key": self._validate_key(storage_key),
            "Body": source,
        }
        if content_type is not None:
            params["ContentType"] = content_type
        try:
            self.client.put_object(**params)
        except Exception as exc:
            raise self._storage_error("Document could not be stored.") from exc
        return size_bytes

    def delete(self, storage_key: str) -> None:
        try:
            self.client.delete_object(
                Bucket=self.bucket,
                Key=self._validate_key(storage_key),
            )
        except Exception as exc:
            raise self._storage_error(
                "Document could not be deleted from storage."
            ) from exc

    def download_path(self, storage_key: str) -> Path:
        raise self._storage_error("S3 documents must be downloaded by presigned URL.")

    def presign_upload(self, storage_key: str, content_type: str) -> PresignedUrl:
        try:
            url = self.presign_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": self._validate_key(storage_key),
                    "ContentType": content_type,
                },
                ExpiresIn=self.expires_in,
            )
        except Exception as exc:
            raise self._storage_error(
                "Document upload URL could not be generated."
            ) from exc
        return PresignedUrl(
            url=url,
            expires_in=self.expires_in,
            headers={"Content-Type": content_type},
        )

    def presign_download(self, storage_key: str) -> PresignedUrl:
        try:
            url = self.presign_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": self._validate_key(storage_key),
                },
                ExpiresIn=self.expires_in,
            )
        except Exception as exc:
            raise self._storage_error(
                "Document download URL could not be generated."
            ) from exc
        return PresignedUrl(
            url=url,
            expires_in=self.expires_in,
            headers={},
        )

    def get_metadata(self, storage_key: str) -> StoredObjectMetadata:
        try:
            response = self.client.head_object(
                Bucket=self.bucket,
                Key=self._validate_key(storage_key),
            )
        except Exception as exc:
            raise self._storage_error(
                "Document could not be read from storage."
            ) from exc
        return StoredObjectMetadata(
            size_bytes=int(response["ContentLength"]),
            content_type=response.get("ContentType"),
        )

    @staticmethod
    def _create_client(
        *,
        endpoint_url: str | None,
        access_key: str | None,
        secret_key: str | None,
        region: str,
    ) -> object:
        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:
            raise AppError(
                status_code=500,
                code="DOCUMENT_STORAGE_ERROR",
                message="S3 storage dependencies are not installed.",
            ) from exc
        return boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(signature_version="s3v4"),
        )

    @staticmethod
    def _source_size(source: BinaryIO) -> int:
        current_position = source.tell()
        source.seek(0, 2)
        size_bytes = source.tell()
        source.seek(current_position)
        return size_bytes

    @staticmethod
    def _validate_key(storage_key: str) -> str:
        key_path = PurePosixPath(storage_key)
        if key_path.is_absolute() or ".." in key_path.parts:
            raise AppError(
                status_code=500,
                code="DOCUMENT_STORAGE_ERROR",
                message="Document storage key is invalid.",
            )
        return storage_key

    @staticmethod
    def _storage_error(message: str) -> AppError:
        return AppError(
            status_code=500,
            code="DOCUMENT_STORAGE_ERROR",
            message=message,
        )


def get_document_storage() -> DocumentStorage:
    if settings.document_storage_backend == "local":
        return LocalDocumentStorage()
    if settings.document_storage_backend == "s3":
        return S3DocumentStorage()
    raise AppError(
        status_code=500,
        code="DOCUMENT_STORAGE_ERROR",
        message="Document storage backend is invalid.",
    )
