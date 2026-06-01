import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import create_app, parse_cors_allowed_origins

pytestmark = [pytest.mark.integration, pytest.mark.anyio]


async def test_configured_cors_origin_is_allowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "cors_allowed_origins", "https://app.example.com")
    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.options(
            "/health",
            headers={
                "Origin": "https://app.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "https://app.example.com"
    )


async def test_cors_is_not_enabled_without_configured_origins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "cors_allowed_origins", "")
    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.options(
            "/health",
            headers={
                "Origin": "https://app.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 405
    assert "access-control-allow-origin" not in response.headers


def test_cors_origin_parser_ignores_blank_entries() -> None:
    assert parse_cors_allowed_origins(
        "https://app.example.com, ,https://admin.example.com,"
    ) == [
        "https://app.example.com",
        "https://admin.example.com",
    ]
