from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.exceptions import AppError
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import TokenResponse, UserCreate, UserLogin, UserRead
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: UserCreate,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if not settings.public_registration_enabled:
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code="PUBLIC_REGISTRATION_DISABLED",
            message="Public registration is disabled.",
        )

    return AuthService(db).register(payload)


@router.post("/login", response_model=TokenResponse)
async def login_user(
    payload: UserLogin,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    return AuthService(db).login(payload)


@router.get("/me", response_model=UserRead)
async def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    return current_user
