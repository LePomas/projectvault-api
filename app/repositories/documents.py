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
    ) -> Document:
        document = Document(
            project_id=project_id,
            uploaded_by_id=uploaded_by_id,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            storage_key=storage_key,
            status="uploaded",
        )
        self.db.add(document)
        self.db.flush()
        return document

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
            )
            .order_by(Document.created_at.desc(), Document.id.desc())
        )
        return list(self.db.scalars(statement).all())

    def get_accessible_by_id(
        self,
        document_id: int,
        user_id: int,
    ) -> Document | None:
        statement = (
            select(Document)
            .join(Project, Project.id == Document.project_id)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(
                Document.id == document_id,
                ProjectMember.user_id == user_id,
                Project.deleted_at.is_(None),
                Document.deleted_at.is_(None),
            )
        )
        return self.db.scalar(statement)

    def update_filename(self, document: Document, filename: str) -> Document:
        document.filename = filename
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
