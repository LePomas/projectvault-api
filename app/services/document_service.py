from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.document import Document
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


@dataclass(frozen=True)
class DocumentDownload:
    document: Document
    path: Path


@dataclass(frozen=True)
class DocumentDownloadUrl:
    url: str
    expires_in: int


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
        project = self.projects.get_accessible_by_id(project_id, current_user.id)
        if project is None:
            raise self._project_not_found()

        filename = self._validate_upload(file)
        storage_key = self.storage.generate_key(project_id, filename)
        file.file.seek(0)
        size_bytes = self.storage.save(storage_key, file.file, file.content_type)

        try:
            document = self.documents.create(
                project_id=project_id,
                uploaded_by_id=current_user.id,
                filename=filename,
                content_type=file.content_type or "",
                size_bytes=size_bytes,
                storage_key=storage_key,
            )
            self.projects.adjust_document_totals(
                project,
                count_delta=1,
                size_delta=size_bytes,
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
        project = self.projects.get_accessible_by_id(project_id, current_user.id)
        if project is None:
            raise self._project_not_found()

        filename = self._validate_file_metadata(
            payload.filename,
            payload.content_type,
        )
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
        document = self.documents.get_accessible_pending_for_project(
            document_id=payload.document_id,
            project_id=project_id,
            user_id=current_user.id,
        )
        if document is None:
            raise self._document_not_found()
        if document.status == "uploaded":
            return document

        metadata = self.storage.get_metadata(document.storage_key)
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
        project = self.projects.get_accessible_by_id(project_id, current_user.id)
        if project is None:
            raise self._project_not_found()
        return self.documents.list_for_accessible_project(project_id, current_user.id)

    def get(self, document_id: int, current_user: User) -> Document:
        document = self.documents.get_accessible_by_id(document_id, current_user.id)
        if document is None:
            raise self._document_not_found()
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
        project = document.project
        count_delta = -1 if document.status == "uploaded" else 0
        size_delta = -document.size_bytes if document.status == "uploaded" else 0

        self.documents.soft_delete(document)
        self.projects.adjust_document_totals(
            project,
            count_delta=count_delta,
            size_delta=size_delta,
        )
        self.db.commit()
        self.storage.delete(document.storage_key)

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
    def _project_not_found() -> AppError:
        return AppError(
            status_code=404,
            code="PROJECT_NOT_FOUND",
            message="Project not found.",
        )

    @staticmethod
    def _document_not_found() -> AppError:
        return AppError(
            status_code=404,
            code="DOCUMENT_NOT_FOUND",
            message="Document not found.",
        )

    @staticmethod
    def _unsupported_type() -> AppError:
        return AppError(
            status_code=415,
            code="UNSUPPORTED_DOCUMENT_TYPE",
            message="Only PDF and DOCX documents are supported.",
        )
