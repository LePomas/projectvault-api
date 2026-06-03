from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project, ProjectInvite, ProjectMember
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

    def create_invite(
        self,
        project_id: int,
        invited_login: str,
        token_hash: str,
        role: str,
        expires_at: datetime,
    ) -> ProjectInvite:
        invite = ProjectInvite(
            project_id=project_id,
            invited_login=invited_login,
            token_hash=token_hash,
            role=role,
            expires_at=expires_at,
        )
        self.db.add(invite)
        self.db.flush()
        return invite

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

    def get_active_by_id(self, project_id: int) -> Project | None:
        statement = select(Project).where(
            Project.id == project_id,
            Project.deleted_at.is_(None),
        )
        return self.db.scalar(statement)

    def get_member(self, project_id: int, user_id: int) -> ProjectMember | None:
        statement = select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
        return self.db.scalar(statement)

    def get_pending_invite(
        self,
        project_id: int,
        invited_login: str,
        now: datetime,
    ) -> ProjectInvite | None:
        statement = select(ProjectInvite).where(
            ProjectInvite.project_id == project_id,
            ProjectInvite.invited_login == invited_login,
            ProjectInvite.accepted_at.is_(None),
            ProjectInvite.expires_at > now,
        )
        return self.db.scalar(statement)

    def get_invite_by_token_hash(self, token_hash: str) -> ProjectInvite | None:
        statement = select(ProjectInvite).where(ProjectInvite.token_hash == token_hash)
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

    def mark_invite_accepted(
        self,
        invite: ProjectInvite,
        accepted_at: datetime,
    ) -> ProjectInvite:
        invite.accepted_at = accepted_at
        self.db.flush()
        return invite

    def update(self, project: Project, fields: dict[str, str | None]) -> Project:
        for field, value in fields.items():
            setattr(project, field, value)
        project.updated_at = datetime.now(UTC)
        self.db.flush()
        return project

    def adjust_document_totals(
        self,
        project: Project,
        *,
        count_delta: int,
        size_delta: int,
    ) -> Project:
        project.documents_count += count_delta
        project.total_size_bytes += size_delta
        project.updated_at = datetime.now(UTC)
        self.db.flush()
        return project

    def soft_delete(self, project: Project) -> Project:
        now = datetime.now(UTC)
        project.deleted_at = now
        project.updated_at = now
        self.db.flush()
        return project
