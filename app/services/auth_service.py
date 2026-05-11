from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.users import UserRepository
from app.schemas.auth import TokenResponse, UserCreate, UserLogin


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    def register(self, payload: UserCreate) -> User:
        email = payload.email.lower()
        if self.users.get_by_login(payload.login) is not None:
            raise AppError(
                status_code=409,
                code="USER_LOGIN_EXISTS",
                message="A user with this login already exists.",
            )
        if self.users.get_by_email(email) is not None:
            raise AppError(
                status_code=409,
                code="USER_EMAIL_EXISTS",
                message="A user with this email already exists.",
            )

        try:
            return self.users.create(
                login=payload.login,
                email=email,
                password_hash=hash_password(payload.password),
            )
        except IntegrityError as exc:
            self.db.rollback()
            raise AppError(
                status_code=409,
                code="USER_ALREADY_EXISTS",
                message="A user with this login or email already exists.",
            ) from exc

    def login(self, payload: UserLogin) -> TokenResponse:
        user = self.users.get_by_login(payload.login)
        if user is None or not verify_password(payload.password, user.password_hash):
            raise AppError(
                status_code=401,
                code="INVALID_CREDENTIALS",
                message="Invalid login or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return TokenResponse(
            access_token=create_access_token(user.id),
            expires_in=settings.jwt_expire_minutes * 60,
        )
