from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.project import Project, ProjectMember


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        project_id: int,
        uploaded_by_id: int,
        filename: str,
        content_type: str,
        size_bytes: int,
        storage_key: str,
        status: str = "uploaded",
    ) -> Document:
        document = Document(
            project_id=project_id,
            uploaded_by_id=uploaded_by_id,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            storage_key=storage_key,
            status=status,
        )
        self.db.add(document)
        self.db.flush()
        return document

    def get_by_storage_key(self, storage_key: str) -> Document | None:
        statement = (
            select(Document)
            .join(Project, Project.id == Document.project_id)
            .where(
                Document.storage_key == storage_key,
                Project.deleted_at.is_(None),
            )
        )
        return self.db.scalar(statement)

    def get_active_pending_for_project(
        self,
        *,
        document_id: int,
        project_id: int,
    ) -> Document | None:
        statement = (
            select(Document)
            .join(Project, Project.id == Document.project_id)
            .where(
                Document.id == document_id,
                Document.project_id == project_id,
                Project.deleted_at.is_(None),
                Document.deleted_at.is_(None),
                Document.status.in_(("pending_upload", "uploaded")),
            )
        )
        return self.db.scalar(statement)

    def list_for_accessible_project(
        self,
        project_id: int,
        user_id: int,
    ) -> list[Document]:
        statement = (
            select(Document)
            .join(Project, Project.id == Document.project_id)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(
                Document.project_id == project_id,
                ProjectMember.user_id == user_id,
                Project.deleted_at.is_(None),
                Document.deleted_at.is_(None),
                Document.status == "uploaded",
            )
            .order_by(Document.created_at.desc(), Document.id.desc())
        )
        return list(self.db.scalars(statement).all())

    def list_uploaded_filenames_by_project_ids(
        self,
        project_ids: list[int],
    ) -> list[tuple[int, str]]:
        if not project_ids:
            return []

        statement = (
            select(Document.project_id, Document.filename)
            .where(
                Document.project_id.in_(project_ids),
                Document.deleted_at.is_(None),
                Document.status == "uploaded",
            )
            .order_by(Document.created_at.desc(), Document.id.desc())
        )
        return [
            (project_id, filename)
            for project_id, filename in self.db.execute(statement)
        ]

    def get_uploaded_by_id(
        self,
        document_id: int,
    ) -> Document | None:
        statement = (
            select(Document)
            .join(Project, Project.id == Document.project_id)
            .where(
                Document.id == document_id,
                Project.deleted_at.is_(None),
                Document.deleted_at.is_(None),
                Document.status == "uploaded",
            )
        )
        return self.db.scalar(statement)

    def update_filename(self, document: Document, filename: str) -> Document:
        document.filename = filename
        document.updated_at = datetime.now(UTC)
        self.db.flush()
        return document

    def mark_uploaded(
        self,
        document: Document,
        *,
        size_bytes: int,
        content_type: str | None,
    ) -> Document:
        document.size_bytes = size_bytes
        if content_type is not None:
            document.content_type = content_type
        document.status = "uploaded"
        document.updated_at = datetime.now(UTC)
        self.db.flush()
        return document

    def soft_delete(self, document: Document) -> Document:
        now = datetime.now(UTC)
        document.status = "deleted"
        document.deleted_at = now
        document.updated_at = now
        self.db.flush()
        return document
