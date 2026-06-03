import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import User

pytestmark = [pytest.mark.integration, pytest.mark.anyio]


async def register_user(
    client: AsyncClient,
    login: str = "ana",
    email: str = "ana@example.com",
    password: str = "super-secret-123",
) -> dict:
    response = await client.post(
        "/auth/register",
        json={
            "login": login,
            "email": email,
            "password": password,
            "repeat_password": password,
        },
    )
    assert response.status_code == 201
    return response.json()


async def test_register_creates_user_without_plain_password(
    client: AsyncClient,
    db_session: Session,
) -> None:
    user = await register_user(client)

    saved_user = db_session.get(User, user["id"])
    assert saved_user is not None
    assert saved_user.login == "ana"
    assert saved_user.email == "ana@example.com"
    assert saved_user.password_hash != "super-secret-123"


async def test_register_can_be_disabled(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "public_registration_enabled", False)

    response = await client.post(
        "/auth/register",
        json={
            "login": "ana",
            "email": "ana@example.com",
            "password": "super-secret-123",
            "repeat_password": "super-secret-123",
        },
    )

    assert response.status_code == 403
    assert_app_error_shape(response.json(), "PUBLIC_REGISTRATION_DISABLED")


async def test_register_rejects_duplicate_login(client: AsyncClient) -> None:
    await register_user(client)

    response = await client.post(
        "/auth/register",
        json={
            "login": "ana",
            "email": "different@example.com",
            "password": "super-secret-123",
            "repeat_password": "super-secret-123",
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "USER_LOGIN_EXISTS"


async def test_register_rejects_duplicate_email(client: AsyncClient) -> None:
    await register_user(client)

    response = await client.post(
        "/auth/register",
        json={
            "login": "different",
            "email": "ana@example.com",
            "password": "super-secret-123",
            "repeat_password": "super-secret-123",
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "USER_EMAIL_EXISTS"


async def test_register_requires_repeat_password(client: AsyncClient) -> None:
    response = await client.post(
        "/auth/register",
        json={
            "login": "ana",
            "email": "ana@example.com",
            "password": "super-secret-123",
        },
    )

    assert response.status_code == 422


async def test_register_rejects_mismatched_repeat_password(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/auth/register",
        json={
            "login": "ana",
            "email": "ana@example.com",
            "password": "super-secret-123",
            "repeat_password": "different-secret-123",
        },
    )

    assert response.status_code == 422


async def test_login_returns_jwt_for_valid_credentials(client: AsyncClient) -> None:
    await register_user(client)

    response = await client.post(
        "/auth/login",
        json={"login": "ana", "password": "super-secret-123"},
    )

    assert response.status_code == 200
    body = response.json()
    decoded = jwt.decode(
        body["access_token"],
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600
    assert decoded["sub"] == "1"


async def test_login_rejects_invalid_password(client: AsyncClient) -> None:
    await register_user(client)

    response = await client.post(
        "/auth/login",
        json={"login": "ana", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_login_rejects_unknown_user(client: AsyncClient) -> None:
    response = await client.post(
        "/auth/login",
        json={"login": "missing", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_me_returns_current_user_with_valid_token(client: AsyncClient) -> None:
    await register_user(client)
    login_response = await client.post(
        "/auth/login",
        json={"login": "ana", "password": "super-secret-123"},
    )

    response = await client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {login_response.json()['access_token']}",
        },
    )

    assert response.status_code == 200
    assert response.json()["login"] == "ana"


async def test_me_rejects_missing_token(client: AsyncClient) -> None:
    response = await client.get("/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "MISSING_TOKEN"


def assert_app_error_shape(response: dict, expected_code: str) -> None:
    assert response["error"]["code"] == expected_code
    assert isinstance(response["error"]["message"], str)
    assert response["error"]["details"] is None


async def test_me_rejects_invalid_token(client: AsyncClient) -> None:
    response = await client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert_app_error_shape(response.json(), "INVALID_TOKEN")
    assert response.headers["WWW-Authenticate"] == "Bearer"


async def test_me_rejects_unsupported_authorization_scheme(client: AsyncClient) -> None:
    response = await client.get(
        "/auth/me",
        headers={"Authorization": "Basic Zm9vOmJhcg=="},
    )

    assert response.status_code == 401
    assert_app_error_shape(response.json(), "MISSING_TOKEN")
    assert response.headers["WWW-Authenticate"] == "Bearer"


async def test_me_rejects_empty_bearer_token(client: AsyncClient) -> None:
    response = await client.get(
        "/auth/me",
        headers={"Authorization": "Bearer"},
    )

    assert response.status_code == 401
    assert_app_error_shape(response.json(), "MISSING_TOKEN")
    assert response.headers["WWW-Authenticate"] == "Bearer"


async def test_me_rejects_expired_token(client: AsyncClient) -> None:
    expired_token = jwt.encode(
        {"sub": "1", "exp": 0},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TOKEN_EXPIRED"


async def test_me_rejects_token_for_missing_user(client: AsyncClient) -> None:
    token = create_access_token(user_id=999)

    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"
