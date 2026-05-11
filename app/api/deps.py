from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.repositories.users import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if token is None:
        raise AppError(
            status_code=401,
            code="MISSING_TOKEN",
            message="Authentication token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = decode_access_token(token)
    user = UserRepository(db).get_by_id(user_id)
    if user is None:
        raise AppError(
            status_code=401,
            code="INVALID_TOKEN",
            message="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
