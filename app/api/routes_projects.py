from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectMemberRead,
    ProjectRead,
    ProjectUpdate,
    ProjectWithDocumentsRead,
)
from app.services.project_service import ProjectService

projects_router = APIRouter(prefix="/projects", tags=["projects"])
project_router = APIRouter(prefix="/project", tags=["projects"])


@project_router.post(
    "",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    payload: ProjectCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Project:
    return ProjectService(db).create(payload, current_user)


@projects_router.get("", response_model=list[ProjectWithDocumentsRead])
async def list_projects(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ProjectWithDocumentsRead]:
    return ProjectService(db).list_accessible_with_document_names(current_user)


@project_router.get("/{project_id}/info", response_model=ProjectRead)
async def get_project_info(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Project:
    return ProjectService(db).get_accessible(project_id, current_user)


@project_router.patch("/{project_id}/info", response_model=ProjectRead)
async def update_project_info(
    project_id: int,
    payload: ProjectUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Project:
    return ProjectService(db).update(project_id, payload, current_user)


@project_router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    ProjectService(db).delete(project_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@project_router.post(
    "/{project_id}/invite",
    response_model=ProjectMemberRead,
    status_code=status.HTTP_201_CREATED,
)
async def grant_project_participant(
    project_id: int,
    user: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ProjectMemberRead:
    return ProjectService(db).grant_participant(project_id, user, current_user)


@project_router.get("/{project_id}/members", response_model=list[ProjectMemberRead])
async def list_project_members(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ProjectMemberRead]:
    return ProjectService(db).list_members(project_id, current_user)


@project_router.delete(
    "/{project_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_project_member(
    project_id: int,
    user_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    ProjectService(db).remove_member(project_id, user_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
