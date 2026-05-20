from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document
from app.models.project import Project

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def document_storage_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    storage_path = tmp_path / "documents"
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
        "/projects",
        headers=bearer(token),
        json={"name": name, "description": "Initial description"},
    )
    assert response.status_code == 201
    return response.json()


async def add_participant(
    client: AsyncClient,
    owner_token: str,
    participant_token: str,
    project_id: int,
    login: str,
) -> None:
    invite_response = await client.post(
        f"/projects/{project_id}/invites",
        headers=bearer(owner_token),
        json={"login": login, "role": "participant"},
    )
    assert invite_response.status_code == 201
    accept_response = await client.post(
        "/invites/accept",
        headers=bearer(participant_token),
        json={"token": invite_response.json()["token"]},
    )
    assert accept_response.status_code == 200


async def upload_pdf(
    client: AsyncClient,
    token: str,
    project_id: int,
    filename: str = "contract.pdf",
    content: bytes = b"%PDF-1.7\nbody",
) -> dict:
    response = await client.post(
        f"/projects/{project_id}/documents",
        headers=bearer(token),
        files={"file": (filename, content, "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()


def stored_file(storage_path: Path, storage_key: str) -> Path:
    return storage_path.joinpath(*storage_key.split("/"))


async def test_owner_can_upload_list_read_rename_and_delete_document(
    client: AsyncClient,
    db_session: Session,
    document_storage_path: Path,
) -> None:
    token = await register_and_login(client, "owner", "owner@example.com")
    project = await create_project(client, token)

    document = await upload_pdf(client, token, project["id"])

    db_session.expire_all()
    saved_document = db_session.get(Document, document["id"])
    saved_project = db_session.get(Project, project["id"])
    assert saved_document is not None
    assert saved_project is not None
    assert document["filename"] == "contract.pdf"
    assert document["content_type"] == "application/pdf"
    assert document["size_bytes"] == len(b"%PDF-1.7\nbody")
    assert document["status"] == "uploaded"
    assert saved_project.documents_count == 1
    assert saved_project.total_size_bytes == len(b"%PDF-1.7\nbody")
    assert stored_file(document_storage_path, document["storage_key"]).read_bytes() == (
        b"%PDF-1.7\nbody"
    )

    list_response = await client.get(
        f"/projects/{project['id']}/documents",
        headers=bearer(token),
    )
    read_response = await client.get(
        f"/documents/{document['id']}",
        headers=bearer(token),
    )
    download_response = await client.get(
        f"/documents/{document['id']}/download",
        headers=bearer(token),
    )
    update_response = await client.put(
        f"/documents/{document['id']}",
        headers=bearer(token),
        json={"filename": "renamed.pdf"},
    )
    delete_response = await client.delete(
        f"/documents/{document['id']}",
        headers=bearer(token),
    )
    deleted_read_response = await client.get(
        f"/documents/{document['id']}",
        headers=bearer(token),
    )
    deleted_download_response = await client.get(
        f"/documents/{document['id']}/download",
        headers=bearer(token),
    )

    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [document["id"]]
    assert read_response.status_code == 200
    assert read_response.json()["id"] == document["id"]
    assert download_response.status_code == 200
    assert download_response.content == b"%PDF-1.7\nbody"
    assert download_response.headers["content-type"] == "application/pdf"
    assert download_response.headers["content-disposition"] == (
        'attachment; filename="contract.pdf"'
    )
    assert update_response.status_code == 200
    assert update_response.json()["filename"] == "renamed.pdf"
    assert delete_response.status_code == 204
    assert deleted_read_response.status_code == 404
    assert deleted_read_response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"
    assert deleted_download_response.status_code == 404
    assert deleted_download_response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"
    assert not stored_file(document_storage_path, document["storage_key"]).exists()

    db_session.expire_all()
    deleted_document = db_session.get(Document, document["id"])
    updated_project = db_session.get(Project, project["id"])
    assert deleted_document is not None
    assert updated_project is not None
    assert deleted_document.deleted_at is not None
    assert deleted_document.status == "deleted"
    assert updated_project.documents_count == 0
    assert updated_project.total_size_bytes == 0


async def test_participant_can_manage_project_documents(
    client: AsyncClient,
) -> None:
    owner_token = await register_and_login(client, "owner", "owner@example.com")
    participant_token = await register_and_login(
        client,
        "participant",
        "participant@example.com",
    )
    project = await create_project(client, owner_token)
    await add_participant(
        client,
        owner_token,
        participant_token,
        project["id"],
        "participant",
    )

    document = await upload_pdf(
        client,
        participant_token,
        project["id"],
        filename="participant.pdf",
    )
    list_response = await client.get(
        f"/projects/{project['id']}/documents",
        headers=bearer(participant_token),
    )
    update_response = await client.put(
        f"/documents/{document['id']}",
        headers=bearer(participant_token),
        json={"filename": "participant-renamed.pdf"},
    )
    download_response = await client.get(
        f"/documents/{document['id']}/download",
        headers=bearer(participant_token),
    )
    delete_response = await client.delete(
        f"/documents/{document['id']}",
        headers=bearer(participant_token),
    )

    assert list_response.status_code == 200
    assert list_response.json()[0]["uploaded_by_id"] == 2
    assert update_response.status_code == 200
    assert update_response.json()["filename"] == "participant-renamed.pdf"
    assert download_response.status_code == 200
    assert download_response.content == b"%PDF-1.7\nbody"
    assert delete_response.status_code == 204


async def test_upload_accepts_docx(client: AsyncClient) -> None:
    token = await register_and_login(client, "owner", "owner@example.com")
    project = await create_project(client, token)

    response = await client.post(
        f"/projects/{project['id']}/documents",
        headers=bearer(token),
        files={
            "file": (
                "brief.docx",
                b"docx bytes",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 201
    assert response.json()["filename"] == "brief.docx"


async def test_download_missing_storage_file_returns_storage_error(
    client: AsyncClient,
    document_storage_path: Path,
) -> None:
    token = await register_and_login(client, "owner", "owner@example.com")
    project = await create_project(client, token)
    document = await upload_pdf(client, token, project["id"])
    stored_file(document_storage_path, document["storage_key"]).unlink()

    response = await client.get(
        f"/documents/{document['id']}/download",
        headers=bearer(token),
    )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "DOCUMENT_STORAGE_ERROR"


async def test_document_endpoints_hide_inaccessible_documents(
    client: AsyncClient,
) -> None:
    owner_token = await register_and_login(client, "owner", "owner@example.com")
    outsider_token = await register_and_login(client, "outsider", "out@example.com")
    project = await create_project(client, owner_token)
    document = await upload_pdf(client, owner_token, project["id"])

    list_response = await client.get(
        f"/projects/{project['id']}/documents",
        headers=bearer(outsider_token),
    )
    read_response = await client.get(
        f"/documents/{document['id']}",
        headers=bearer(outsider_token),
    )
    download_response = await client.get(
        f"/documents/{document['id']}/download",
        headers=bearer(outsider_token),
    )
    update_response = await client.put(
        f"/documents/{document['id']}",
        headers=bearer(outsider_token),
        json={"filename": "stolen.pdf"},
    )
    delete_response = await client.delete(
        f"/documents/{document['id']}",
        headers=bearer(outsider_token),
    )

    assert list_response.status_code == 404
    assert list_response.json()["error"]["code"] == "PROJECT_NOT_FOUND"
    assert read_response.status_code == 404
    assert read_response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"
    assert download_response.status_code == 404
    assert download_response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"
    assert update_response.status_code == 404
    assert update_response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"
    assert delete_response.status_code == 404
    assert delete_response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"


async def test_upload_rejects_unsupported_extension_and_content_type(
    client: AsyncClient,
) -> None:
    token = await register_and_login(client, "owner", "owner@example.com")
    project = await create_project(client, token)

    extension_response = await client.post(
        f"/projects/{project['id']}/documents",
        headers=bearer(token),
        files={"file": ("notes.txt", b"notes", "text/plain")},
    )
    content_type_response = await client.post(
        f"/projects/{project['id']}/documents",
        headers=bearer(token),
        files={"file": ("contract.pdf", b"fake", "text/plain")},
    )

    assert extension_response.status_code == 415
    assert extension_response.json()["error"]["code"] == "UNSUPPORTED_DOCUMENT_TYPE"
    assert content_type_response.status_code == 415
    assert content_type_response.json()["error"]["code"] == (
        "UNSUPPORTED_DOCUMENT_TYPE"
    )


async def test_document_endpoints_require_authentication(
    client: AsyncClient,
) -> None:
    upload_response = await client.post(
        "/projects/1/documents",
        files={"file": ("contract.pdf", b"%PDF", "application/pdf")},
    )
    list_response = await client.get("/projects/1/documents")
    read_response = await client.get("/documents/1")
    download_response = await client.get("/documents/1/download")
    update_response = await client.put("/documents/1", json={"filename": "x.pdf"})
    delete_response = await client.delete("/documents/1")

    assert upload_response.status_code == 401
    assert upload_response.json()["error"]["code"] == "MISSING_TOKEN"
    assert list_response.status_code == 401
    assert list_response.json()["error"]["code"] == "MISSING_TOKEN"
    assert read_response.status_code == 401
    assert read_response.json()["error"]["code"] == "MISSING_TOKEN"
    assert download_response.status_code == 401
    assert download_response.json()["error"]["code"] == "MISSING_TOKEN"
    assert update_response.status_code == 401
    assert update_response.json()["error"]["code"] == "MISSING_TOKEN"
    assert delete_response.status_code == 401
    assert delete_response.json()["error"]["code"] == "MISSING_TOKEN"
