from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.document import Document
from app.models.user import User
from app.repositories.documents import DocumentRepository
from app.repositories.projects import ProjectRepository
from app.schemas.document import DocumentUpdate
from app.services.storage import LocalDocumentStorage

ALLOWED_DOCUMENT_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class DocumentService:
    def __init__(
        self,
        db: Session,
        storage: LocalDocumentStorage | None = None,
    ) -> None:
        self.db = db
        self.documents = DocumentRepository(db)
        self.projects = ProjectRepository(db)
        self.storage = storage or LocalDocumentStorage()

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
        size_bytes = self.storage.save(storage_key, file.file)

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

        self.documents.soft_delete(document)
        self.projects.adjust_document_totals(
            project,
            count_delta=-1,
            size_delta=-document.size_bytes,
        )
        self.db.commit()
        self.storage.delete(document.storage_key)

    @staticmethod
    def _validate_upload(file: UploadFile) -> str:
        filename = Path(file.filename or "").name
        suffix = Path(filename).suffix.lower()
        if not filename or suffix not in ALLOWED_DOCUMENT_TYPES:
            raise DocumentService._unsupported_type()
        if file.content_type != ALLOWED_DOCUMENT_TYPES[suffix]:
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
