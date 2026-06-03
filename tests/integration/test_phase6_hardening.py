"""
Phase 6 hardening tests for pending upload visibility, soft-delete consistency,
and storage limit behavior across all upload paths.
"""

from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.storage import PresignedUrl, StoredObjectMetadata

pytestmark = [pytest.mark.integration, pytest.mark.anyio]


class FakeS3Storage:
    def __init__(self) -> None:
        self.objects: dict[str, StoredObjectMetadata] = {}
        self.deleted_keys: list[str] = []

    def generate_key(self, project_id: int, filename: str) -> str:
        suffix = Path(filename).suffix.lower()
        return f"projects/{project_id}/fake-s3-document{suffix}"

    def save(self, storage_key, source, content_type=None):
        raise AssertionError("S3 API tests should not use multipart save")

    def delete(self, storage_key: str) -> None:
        self.deleted_keys.append(storage_key)
        self.objects.pop(storage_key, None)

    def download_path(self, storage_key: str):
        raise AssertionError("S3 API tests should not use local download paths")

    def presign_upload(self, storage_key: str, content_type: str) -> PresignedUrl:
        return PresignedUrl(
            url=f"http://localhost:9000/projectvault-documents/{storage_key}?upload",
            expires_in=900,
            headers={"Content-Type": content_type},
        )

    def presign_download(self, storage_key: str) -> PresignedUrl:
        return PresignedUrl(
            url=f"http://localhost:9000/projectvault-documents/{storage_key}?download",
            expires_in=900,
            headers={},
        )

    def get_metadata(self, storage_key: str) -> StoredObjectMetadata:
        try:
            return self.objects[storage_key]
        except KeyError as exc:
            from app.core.exceptions import AppError

            raise AppError(
                status_code=500,
                code="DOCUMENT_STORAGE_ERROR",
                message="Document could not be read from storage.",
            ) from exc


@pytest.fixture
def fake_s3_storage(monkeypatch: pytest.MonkeyPatch) -> FakeS3Storage:
    storage = FakeS3Storage()
    monkeypatch.setattr(
        "app.services.document_service.get_document_storage",
        lambda: storage,
    )
    return storage


@pytest.fixture(autouse=True)
def document_storage_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    storage_path = tmp_path / "documents"
    monkeypatch.setattr(settings, "document_storage_backend", "local")
    monkeypatch.setattr(settings, "document_storage_path", str(storage_path))
    return storage_path


async def register_and_login(
    client: AsyncClient,
    login: str,
    email: str,
) -> str:
    await client.post(
        "/auth/register",
        json={
            "login": login,
            "email": email,
            "password": "super-secret-123",
            "repeat_password": "super-secret-123",
        },
    )
    response = await client.post(
        "/auth/login",
        json={"login": login, "password": "super-secret-123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def create_project(
    client: AsyncClient,
    token: str,
    name: str = "Project Alpha",
) -> dict:
    response = await client.post(
        "/project",
        headers=bearer(token),
        json={"name": name, "description": "Initial description"},
    )
    assert response.status_code == 201
    return response.json()


async def test_pending_uploads_hidden_from_list_documents(
    client: AsyncClient,
    fake_s3_storage,
) -> None:
    """Pending uploads should not appear in GET /projects/{project_id}/documents"""
    token = await register_and_login(client, "owner", "owner@example.com")
    project = await create_project(client, token)

    # Create pending upload
    presign_response = await client.post(
        f"/project/{project['id']}/documents/presign-upload",
        headers=bearer(token),
        json={"filename": "contract.pdf", "content_type": "application/pdf"},
    )
    assert presign_response.status_code == 201

    # List should not include pending document
    list_response = await client.get(
        f"/project/{project['id']}/documents",
        headers=bearer(token),
    )
    assert list_response.status_code == 200
    assert len(list_response.json()) == 0


async def test_pending_uploads_hidden_from_get_document(
    client: AsyncClient,
    fake_s3_storage,
) -> None:
    """Pending uploads should not be accessible via GET /documents/{document_id}"""
    token = await register_and_login(client, "owner", "owner@example.com")
    project = await create_project(client, token)

    # Create pending upload
    presign_response = await client.post(
        f"/project/{project['id']}/documents/presign-upload",
        headers=bearer(token),
        json={"filename": "contract.pdf", "content_type": "application/pdf"},
    )
    assert presign_response.status_code == 201
    document_id = presign_response.json()["document_id"]

    # Direct GET should return 404
    get_response = await client.get(
        f"/document/{document_id}",
        headers=bearer(token),
    )
    assert get_response.status_code == 404
    assert get_response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"


async def test_storage_limit_consistent_across_s3_uploads(
    client: AsyncClient,
    db_session: Session,
    fake_s3_storage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Storage limits should be enforced consistently across presigned upload paths"""
    # Set a small storage limit (5KB)
    monkeypatch.setattr(settings, "project_storage_limit_bytes", 5000)

    token = await register_and_login(client, "owner", "owner@example.com")
    project = await create_project(client, token)

    # Try presigned upload that would exceed limit
    presign_response = await client.post(
        f"/project/{project['id']}/documents/presign-upload",
        headers=bearer(token),
        json={
            "filename": "large.pdf",
            "content_type": "application/pdf",
            "size_bytes": 6000,
        },
    )
    assert presign_response.status_code == 413
    assert presign_response.json()["error"]["code"] == "PROJECT_STORAGE_LIMIT_EXCEEDED"
