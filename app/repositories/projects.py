from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project, ProjectMember
from app.models.user import User


class ProjectRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, name: str, description: str | None, owner_id: int) -> Project:
        project = Project(name=name, description=description, owner_id=owner_id)
        self.db.add(project)
        self.db.flush()
        return project

    def add_member(self, project_id: int, user_id: int, role: str) -> ProjectMember:
        member = ProjectMember(project_id=project_id, user_id=user_id, role=role)
        self.db.add(member)
        self.db.flush()
        return member

    def list_accessible(self, user_id: int) -> list[Project]:
        statement = (
            select(Project)
            .join(ProjectMember)
            .where(
                ProjectMember.user_id == user_id,
                Project.deleted_at.is_(None),
            )
            .order_by(Project.created_at.desc(), Project.id.desc())
        )
        return list(self.db.scalars(statement).all())

    def get_accessible_by_id(self, project_id: int, user_id: int) -> Project | None:
        statement = (
            select(Project)
            .join(ProjectMember)
            .where(
                Project.id == project_id,
                ProjectMember.user_id == user_id,
                Project.deleted_at.is_(None),
            )
        )
        return self.db.scalar(statement)

    def get_member(self, project_id: int, user_id: int) -> ProjectMember | None:
        statement = select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
        return self.db.scalar(statement)

    def list_members(self, project_id: int) -> list[tuple[ProjectMember, User]]:
        statement = (
            select(ProjectMember, User)
            .join(User, User.id == ProjectMember.user_id)
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.created_at.asc(), ProjectMember.id.asc())
        )
        return list(self.db.execute(statement).all())

    def delete_member(self, member: ProjectMember) -> None:
        self.db.delete(member)
        self.db.flush()

    def update(self, project: Project, fields: dict[str, str | None]) -> Project:
        for field, value in fields.items():
            setattr(project, field, value)
        project.updated_at = datetime.now(UTC)
        self.db.flush()
        return project

    def soft_delete(self, project: Project) -> Project:
        now = datetime.now(UTC)
        project.deleted_at = now
        project.updated_at = now
        self.db.flush()
        return project
