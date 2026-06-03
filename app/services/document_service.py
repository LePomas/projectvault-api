from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppError
from app.models.document import Document
from app.models.project import Project
from app.models.user import User
from app.repositories.documents import DocumentRepository
from app.repositories.projects import ProjectRepository
from app.schemas.document import (
    DocumentCompleteUploadRequest,
    DocumentPresignUploadRead,
    DocumentPresignUploadRequest,
    DocumentUpdate,
)
from app.services.storage import DocumentStorage, get_document_storage

ALLOWED_DOCUMENT_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
OWNER_ROLE = "owner"


@dataclass(frozen=True)
class DocumentDownload:
    document: Document
    path: Path


@dataclass(frozen=True)
class DocumentDownloadUrl:
    url: str
    expires_in: int


@dataclass(frozen=True)
class DocumentUploadEventResult:
    storage_key: str
    status: str
    document_id: int | None = None
    reason: str | None = None
    size_bytes: int | None = None


class DocumentService:
    def __init__(
        self,
        db: Session,
        storage: DocumentStorage | None = None,
    ) -> None:
        self.db = db
        self.documents = DocumentRepository(db)
        self.projects = ProjectRepository(db)
        self.storage = storage or get_document_storage()

    def upload(
        self,
        project_id: int,
        file: UploadFile,
        current_user: User,
    ) -> Document:
        project = self._get_accessible_project(project_id, current_user)

        filename = self._validate_upload(file)
        size_bytes = self._source_size(file.file)
        self._ensure_storage_available(project, size_bytes)
        storage_key = self.storage.generate_key(project_id, filename)
        file.file.seek(0)
        saved_size_bytes = self.storage.save(storage_key, file.file, file.content_type)

        try:
            document = self.documents.create(
                project_id=project_id,
                uploaded_by_id=current_user.id,
                filename=filename,
                content_type=file.content_type or "",
                size_bytes=saved_size_bytes,
                storage_key=storage_key,
            )
            self.projects.adjust_document_totals(
                project,
                count_delta=1,
                size_delta=saved_size_bytes,
            )
            self.db.commit()
            self.db.refresh(document)
            return document
        except IntegrityError as exc:
            self.db.rollback()
            self.storage.delete(storage_key)
            raise AppError(
                status_code=409,
                code="DOCUMENT_CREATE_CONFLICT",
                message="Document could not be created.",
            ) from exc

    def presign_upload(
        self,
        project_id: int,
        payload: DocumentPresignUploadRequest,
        current_user: User,
    ) -> DocumentPresignUploadRead:
        project = self._get_accessible_project(project_id, current_user)

        filename = self._validate_file_metadata(
            payload.filename,
            payload.content_type,
        )
        if payload.size_bytes is not None:
            self._ensure_storage_available(project, payload.size_bytes)
        storage_key = self.storage.generate_key(project_id, filename)
        presigned = self.storage.presign_upload(storage_key, payload.content_type)

        try:
            document = self.documents.create(
                project_id=project_id,
                uploaded_by_id=current_user.id,
                filename=filename,
                content_type=payload.content_type,
                size_bytes=0,
                storage_key=storage_key,
                status="pending_upload",
            )
            self.db.commit()
            self.db.refresh(document)
        except IntegrityError as exc:
            self.db.rollback()
            raise AppError(
                status_code=409,
                code="DOCUMENT_CREATE_CONFLICT",
                message="Document could not be created.",
            ) from exc

        return DocumentPresignUploadRead(
            document_id=document.id,
            storage_key=document.storage_key,
            upload_url=presigned.url,
            headers=dict(presigned.headers),
            expires_in=presigned.expires_in,
        )

    def complete_upload(
        self,
        project_id: int,
        payload: DocumentCompleteUploadRequest,
        current_user: User,
    ) -> Document:
        document = self.documents.get_active_pending_for_project(
            document_id=payload.document_id,
            project_id=project_id,
        )
        if document is None:
            raise self._document_not_found()
        if self.projects.get_member(project_id, current_user.id) is None:
            raise self._document_forbidden()
        if document.status == "uploaded":
            return document

        completed_document = self._complete_pending_upload(
            document,
            raise_on_limit=True,
        )
        if completed_document is None:
            raise self._document_not_found()
        return completed_document

    def complete_upload_by_storage_key(
        self,
        storage_key: str,
    ) -> DocumentUploadEventResult:
        document = self.documents.get_by_storage_key(storage_key)
        if document is None:
            return DocumentUploadEventResult(
                storage_key=storage_key,
                status="skipped",
                reason="document_not_found",
            )
        if document.deleted_at is not None or document.status == "deleted":
            return DocumentUploadEventResult(
                storage_key=storage_key,
                status="skipped",
                document_id=document.id,
                reason="document_deleted",
            )
        if document.status == "uploaded":
            return DocumentUploadEventResult(
                storage_key=storage_key,
                status="already_uploaded",
                document_id=document.id,
                size_bytes=document.size_bytes,
            )
        if document.status != "pending_upload":
            return DocumentUploadEventResult(
                storage_key=storage_key,
                status="skipped",
                document_id=document.id,
                reason="unsupported_document_status",
            )

        document_id = document.id
        document = self._complete_pending_upload(document, raise_on_limit=False)
        if document is None:
            return DocumentUploadEventResult(
                storage_key=storage_key,
                status="rejected",
                document_id=document_id,
                reason="storage_limit_exceeded",
            )
        return DocumentUploadEventResult(
            storage_key=storage_key,
            status="uploaded",
            document_id=document.id,
            size_bytes=document.size_bytes,
        )

    def _complete_pending_upload(
        self,
        document: Document,
        *,
        raise_on_limit: bool,
    ) -> Document | None:
        metadata = self.storage.get_metadata(document.storage_key)
        if not self._has_storage_available(document.project, metadata.size_bytes):
            self.storage.delete(document.storage_key)
            self.documents.soft_delete(document)
            self.db.commit()
            if raise_on_limit:
                raise self._storage_limit_exceeded(
                    document.project,
                    metadata.size_bytes,
                )
            return None

        try:
            document = self.documents.mark_uploaded(
                document,
                size_bytes=metadata.size_bytes,
                content_type=metadata.content_type,
            )
            self.projects.adjust_document_totals(
                document.project,
                count_delta=1,
                size_delta=metadata.size_bytes,
            )
            self.db.commit()
            self.db.refresh(document)
            return document
        except IntegrityError as exc:
            self.db.rollback()
            raise AppError(
                status_code=409,
                code="DOCUMENT_UPDATE_CONFLICT",
                message="Document could not be updated.",
            ) from exc

    def list_for_project(self, project_id: int, current_user: User) -> list[Document]:
        self._get_accessible_project(project_id, current_user)
        return self.documents.list_for_accessible_project(project_id, current_user.id)

    def get(self, document_id: int, current_user: User) -> Document:
        document = self.documents.get_uploaded_by_id(document_id)
        if document is None:
            raise self._document_not_found()
        if self.projects.get_member(document.project_id, current_user.id) is None:
            raise self._document_forbidden()
        return document

    def download(self, document_id: int, current_user: User) -> DocumentDownload:
        document = self.get(document_id, current_user)
        if document.status != "uploaded":
            raise self._document_not_found()
        return DocumentDownload(
            document=document,
            path=self.storage.download_path(document.storage_key),
        )

    def download_url(
        self,
        document_id: int,
        current_user: User,
    ) -> DocumentDownloadUrl:
        document = self.get(document_id, current_user)
        if document.status != "uploaded":
            raise self._document_not_found()
        presigned = self.storage.presign_download(document.storage_key)
        return DocumentDownloadUrl(
            url=presigned.url,
            expires_in=presigned.expires_in,
        )

    def update(
        self,
        document_id: int,
        payload: DocumentUpdate,
        current_user: User,
    ) -> Document:
        document = self.get(document_id, current_user)
        try:
            document = self.documents.update_filename(document, payload.filename)
            self.db.commit()
            self.db.refresh(document)
            return document
        except IntegrityError as exc:
            self.db.rollback()
            raise AppError(
                status_code=409,
                code="DOCUMENT_UPDATE_CONFLICT",
                message="Document could not be updated.",
            ) from exc

    def delete(self, document_id: int, current_user: User) -> None:
        document = self.get(document_id, current_user)
        member = self.projects.get_member(document.project_id, current_user.id)
        if member is None or member.role != OWNER_ROLE:
            raise self._document_forbidden()

        project = document.project

        try:
            self.storage.delete(document.storage_key)
        except AppError:
            self.db.rollback()
            raise

        self.documents.soft_delete(document)
        self.projects.adjust_document_totals(
            project,
            count_delta=-1,
            size_delta=-document.size_bytes,
        )
        self.db.commit()

    def _get_accessible_project(self, project_id: int, current_user: User) -> Project:
        project = self.projects.get_active_by_id(project_id)
        if project is None:
            raise self._project_not_found()
        if self.projects.get_member(project_id, current_user.id) is None:
            raise self._project_forbidden()
        return project

    @staticmethod
    def _validate_upload(file: UploadFile) -> str:
        return DocumentService._validate_file_metadata(
            file.filename or "",
            file.content_type or "",
        )

    @staticmethod
    def _validate_file_metadata(filename: str, content_type: str) -> str:
        filename = Path(filename).name
        suffix = Path(filename).suffix.lower()
        if not filename or suffix not in ALLOWED_DOCUMENT_TYPES:
            raise DocumentService._unsupported_type()
        if content_type != ALLOWED_DOCUMENT_TYPES[suffix]:
            raise DocumentService._unsupported_type()
        return filename

    @staticmethod
    def _source_size(source: BinaryIO) -> int:
        current_position = source.tell()
        source.seek(0, 2)
        size_bytes = source.tell()
        source.seek(current_position)
        return size_bytes

    @staticmethod
    def _has_storage_available(project: Project, requested_size_bytes: int) -> bool:
        limit = settings.project_storage_limit_bytes
        if limit <= 0:
            return True
        return project.total_size_bytes + requested_size_bytes <= limit

    @staticmethod
    def _ensure_storage_available(
        project: Project,
        requested_size_bytes: int,
    ) -> None:
        if not DocumentService._has_storage_available(project, requested_size_bytes):
            raise DocumentService._storage_limit_exceeded(project, requested_size_bytes)

    @staticmethod
    def _project_not_found() -> AppError:
        return AppError(
            status_code=404,
            code="PROJECT_NOT_FOUND",
            message="Project not found.",
        )

    @staticmethod
    def _project_forbidden() -> AppError:
        return AppError(
            status_code=403,
            code="PROJECT_FORBIDDEN",
            message="You do not have permission to access this project.",
        )

    @staticmethod
    def _document_not_found() -> AppError:
        return AppError(
            status_code=404,
            code="DOCUMENT_NOT_FOUND",
            message="Document not found.",
        )

    @staticmethod
    def _document_forbidden() -> AppError:
        return AppError(
            status_code=403,
            code="DOCUMENT_FORBIDDEN",
            message="You do not have permission to access this document.",
        )

    @staticmethod
    def _unsupported_type() -> AppError:
        return AppError(
            status_code=415,
            code="UNSUPPORTED_DOCUMENT_TYPE",
            message="Only PDF and DOCX documents are supported.",
        )

    @staticmethod
    def _storage_limit_exceeded(
        project: Project,
        requested_size_bytes: int,
    ) -> AppError:
        return AppError(
            status_code=413,
            code="PROJECT_STORAGE_LIMIT_EXCEEDED",
            message="Project storage limit would be exceeded.",
            details={
                "limit_bytes": settings.project_storage_limit_bytes,
                "current_size_bytes": project.total_size_bytes,
                "requested_size_bytes": requested_size_bytes,
            },
        )
