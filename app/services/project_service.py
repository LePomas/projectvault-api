import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.project import Project, ProjectInvite, ProjectMember
from app.models.user import User
from app.repositories.projects import ProjectRepository
from app.repositories.users import UserRepository
from app.schemas.project import (
    ProjectCreate,
    ProjectInviteAccept,
    ProjectInviteCreate,
    ProjectInviteRead,
    ProjectMemberRead,
    ProjectUpdate,
)

OWNER_ROLE = "owner"
PARTICIPANT_ROLE = "participant"
INVITE_EXPIRE_DAYS = 7


class ProjectService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.projects = ProjectRepository(db)
        self.users = UserRepository(db)

    def create(self, payload: ProjectCreate, current_user: User) -> Project:
        try:
            project = self.projects.create(
                name=payload.name,
                description=payload.description,
                owner_id=current_user.id,
            )
            self.projects.add_member(
                project_id=project.id,
                user_id=current_user.id,
                role=OWNER_ROLE,
            )
            self.db.commit()
            self.db.refresh(project)
            return project
        except IntegrityError as exc:
            self.db.rollback()
            raise AppError(
                status_code=409,
                code="PROJECT_CREATE_CONFLICT",
                message="Project could not be created.",
            ) from exc

    def list_accessible(self, current_user: User) -> list[Project]:
        return self.projects.list_accessible(current_user.id)

    def get_accessible(self, project_id: int, current_user: User) -> Project:
        project = self.projects.get_active_by_id(project_id)
        if project is None:
            raise self._not_found()
        if self.projects.get_member(project_id, current_user.id) is None:
            raise self._forbidden()
        return project

    def update(
        self,
        project_id: int,
        payload: ProjectUpdate,
        current_user: User,
    ) -> Project:
        project = self.get_accessible(project_id, current_user)
        update_fields = payload.model_dump(exclude_unset=True)
        if not update_fields:
            return project

        try:
            project = self.projects.update(project, update_fields)
            self.db.commit()
            self.db.refresh(project)
            return project
        except IntegrityError as exc:
            self.db.rollback()
            raise AppError(
                status_code=409,
                code="PROJECT_UPDATE_CONFLICT",
                message="Project could not be updated.",
            ) from exc

    def delete(self, project_id: int, current_user: User) -> None:
        project = self._require_owner(project_id, current_user)

        self.projects.soft_delete(project)
        self.db.commit()

    def invite_member(
        self,
        project_id: int,
        payload: ProjectInviteCreate,
        current_user: User,
    ) -> ProjectInviteRead:
        self._require_owner(project_id, current_user)
        invited_user = self.users.get_by_login(payload.login)
        if invited_user is None:
            raise AppError(
                status_code=404,
                code="USER_NOT_FOUND",
                message="User not found.",
            )
        if self.projects.get_member(project_id, invited_user.id) is not None:
            raise AppError(
                status_code=409,
                code="PROJECT_MEMBER_EXISTS",
                message="User is already a project member.",
            )

        now = datetime.now(UTC)
        if self.projects.get_pending_invite(project_id, payload.login, now) is not None:
            raise AppError(
                status_code=409,
                code="PROJECT_INVITE_EXISTS",
                message="A pending invite already exists for this user.",
            )

        token = secrets.token_urlsafe(32)
        expires_at = now + timedelta(days=INVITE_EXPIRE_DAYS)

        try:
            invite = self.projects.create_invite(
                project_id=project_id,
                invited_login=payload.login,
                token_hash=self._token_hash(token),
                role=payload.role,
                expires_at=expires_at,
            )
            self.db.commit()
            self.db.refresh(invite)
        except IntegrityError as exc:
            self.db.rollback()
            raise AppError(
                status_code=409,
                code="PROJECT_INVITE_CONFLICT",
                message="Project invite could not be created.",
            ) from exc

        return self._invite_read(invite, token)

    def accept_invite(
        self,
        payload: ProjectInviteAccept,
        current_user: User,
    ) -> ProjectMemberRead:
        invite = self.projects.get_invite_by_token_hash(
            self._token_hash(payload.token),
        )
        if invite is None:
            raise AppError(
                status_code=404,
                code="PROJECT_INVITE_NOT_FOUND",
                message="Project invite not found.",
            )
        if invite.accepted_at is not None:
            raise AppError(
                status_code=409,
                code="PROJECT_INVITE_ACCEPTED",
                message="Project invite has already been accepted.",
            )
        if self._is_expired(invite.expires_at):
            raise AppError(
                status_code=410,
                code="PROJECT_INVITE_EXPIRED",
                message="Project invite has expired.",
            )
        if invite.invited_login != current_user.login:
            raise AppError(
                status_code=404,
                code="PROJECT_INVITE_NOT_FOUND",
                message="Project invite not found.",
            )

        try:
            member = self.projects.add_member(
                project_id=invite.project_id,
                user_id=current_user.id,
                role=invite.role,
            )
            self.projects.mark_invite_accepted(invite, datetime.now(UTC))
            self.db.commit()
            self.db.refresh(member)
        except IntegrityError as exc:
            self.db.rollback()
            raise AppError(
                status_code=409,
                code="PROJECT_MEMBER_EXISTS",
                message="User is already a project member.",
            ) from exc

        return self._member_read(member, current_user)

    def list_members(
        self,
        project_id: int,
        current_user: User,
    ) -> list[ProjectMemberRead]:
        self.get_accessible(project_id, current_user)
        return [
            self._member_read(member, user)
            for member, user in self.projects.list_members(project_id)
        ]

    def remove_member(
        self,
        project_id: int,
        user_id: int,
        current_user: User,
    ) -> None:
        self._require_owner(project_id, current_user)
        member = self.projects.get_member(project_id, user_id)
        if member is None:
            raise self._not_found()
        if member.role != PARTICIPANT_ROLE:
            raise self._forbidden()

        self.projects.delete_member(member)
        self.db.commit()

    def _require_owner(self, project_id: int, current_user: User) -> Project:
        project = self.projects.get_active_by_id(project_id)
        if project is None:
            raise self._not_found()
        member = self.projects.get_member(project_id, current_user.id)
        if member is None or member.role != OWNER_ROLE:
            raise self._forbidden()
        return project

    @staticmethod
    def _member_read(member: ProjectMember, user: User) -> ProjectMemberRead:
        return ProjectMemberRead(
            id=member.id,
            project_id=member.project_id,
            user_id=member.user_id,
            login=user.login,
            role=member.role,
            created_at=member.created_at,
        )

    @staticmethod
    def _invite_read(invite: ProjectInvite, token: str) -> ProjectInviteRead:
        return ProjectInviteRead(
            id=invite.id,
            project_id=invite.project_id,
            invited_login=invite.invited_login or "",
            role=invite.role,
            token=token,
            expires_at=invite.expires_at,
            created_at=invite.created_at,
        )

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def _is_expired(expires_at: datetime) -> bool:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return expires_at <= datetime.now(UTC)

    @staticmethod
    def _not_found() -> AppError:
        return AppError(
            status_code=404,
            code="PROJECT_NOT_FOUND",
            message="Project not found.",
        )

    @staticmethod
    def _forbidden() -> AppError:
        return AppError(
            status_code=403,
            code="PROJECT_FORBIDDEN",
            message="You do not have permission to access this project.",
        )
