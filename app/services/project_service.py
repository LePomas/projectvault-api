from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.project import Project, ProjectMember
from app.models.user import User
from app.repositories.documents import DocumentRepository
from app.repositories.projects import ProjectRepository
from app.repositories.users import UserRepository
from app.schemas.project import (
    ProjectCreate,
    ProjectMemberRead,
    ProjectRead,
    ProjectUpdate,
    ProjectWithDocumentsRead,
)

OWNER_ROLE = "owner"
PARTICIPANT_ROLE = "participant"


class ProjectService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.projects = ProjectRepository(db)
        self.documents = DocumentRepository(db)
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

    def list_accessible_with_document_names(
        self,
        current_user: User,
    ) -> list[ProjectWithDocumentsRead]:
        projects = self.projects.list_accessible(current_user.id)
        filenames_by_project_id = {project.id: [] for project in projects}
        project_ids = [project.id for project in projects]
        filenames = self.documents.list_uploaded_filenames_by_project_ids(project_ids)
        for project_id, filename in filenames:
            filenames_by_project_id[project_id].append(filename)

        project_reads = [ProjectRead.model_validate(project) for project in projects]
        return [
            ProjectWithDocumentsRead(
                **project_read.model_dump(),
                documents=filenames_by_project_id[project_read.id],
            )
            for project_read in project_reads
        ]

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

    def grant_participant(
        self,
        project_id: int,
        login: str,
        current_user: User,
    ) -> ProjectMemberRead:
        self._require_owner(project_id, current_user)
        invited_user = self.users.get_by_login(login)
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

        try:
            member = self.projects.add_member(
                project_id=project_id,
                user_id=invited_user.id,
                role=PARTICIPANT_ROLE,
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
