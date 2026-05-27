from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.project import ProjectInviteAccept, ProjectMemberRead
from app.services.project_service import ProjectService

router = APIRouter(prefix="/invites", tags=["invites"])


@router.post("/accept", response_model=ProjectMemberRead, status_code=status.HTTP_201_CREATED)
async def accept_project_invite(
    payload: ProjectInviteAccept,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ProjectMemberRead:
    return ProjectService(db).accept_invite(payload, current_user)
