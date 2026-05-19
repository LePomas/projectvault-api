from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.project import Project, ProjectMember
from app.models.user import User
from app.repositories.projects import ProjectRepository
from app.repositories.users import UserRepository
from app.schemas.project import (
    ProjectCreate,
    ProjectInviteCreate,
    ProjectMemberRead,
    ProjectUpdate,
)

OWNER_ROLE = "owner"
PARTICIPANT_ROLE = "participant"


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
        project = self.projects.get_accessible_by_id(project_id, current_user.id)
        if project is None:
            raise self._not_found()
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
        project = self.projects.get_accessible_by_id(project_id, current_user.id)
        member = self.projects.get_member(project_id, current_user.id)
        if project is None or member is None or member.role != OWNER_ROLE:
            raise self._not_found()

        self.projects.soft_delete(project)
        self.db.commit()

    def invite_member(
        self,
        project_id: int,
        payload: ProjectInviteCreate,
        current_user: User,
    ) -> ProjectMemberRead:
        self._require_owner(project_id, current_user)
        invited_user = self.users.get_by_login(payload.login)
        if invited_user is None:
            raise AppError(
                status_code=404,
                code="USER_NOT_FOUND",
                message="User not found.",
            )

        try:
            member = self.projects.add_member(
                project_id=project_id,
                user_id=invited_user.id,
                role=payload.role,
            )
            self.db.commit()
            self.db.refresh(member)
        except IntegrityError as exc:
            self.db.rollback()
            raise AppError(
                status_code=409,
                code="PROJECT_MEMBER_EXISTS",
                message="User is already a project member.",
            ) from exc

        return self._member_read(member, invited_user)

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
        if member is None or member.role != PARTICIPANT_ROLE:
            raise self._not_found()

        self.projects.delete_member(member)
        self.db.commit()

    def _require_owner(self, project_id: int, current_user: User) -> Project:
        project = self.projects.get_accessible_by_id(project_id, current_user.id)
        member = self.projects.get_member(project_id, current_user.id)
        if project is None or member is None or member.role != OWNER_ROLE:
            raise self._not_found()
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
    def _not_found() -> AppError:
        return AppError(
            status_code=404,
            code="PROJECT_NOT_FOUND",
            message="Project not found.",
        )
