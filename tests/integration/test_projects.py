import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.project import Project, ProjectMember

pytestmark = [pytest.mark.integration, pytest.mark.anyio]


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
    description: str | None = "Initial description",
) -> dict:
    response = await client.post(
        "/project",
        headers=bearer(token),
        json={"name": name, "description": description},
    )
    assert response.status_code == 201
    return response.json()


async def upload_pdf(
    client: AsyncClient,
    token: str,
    project_id: int,
    filename: str = "contract.pdf",
) -> dict:
    response = await client.post(
        f"/project/{project_id}/documents",
        headers=bearer(token),
        files={"file": (filename, b"%PDF-1.7\nbody", "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()


async def grant_participant(
    client: AsyncClient,
    token: str,
    project_id: int,
    login: str,
) -> dict:
    response = await client.post(
        f"/project/{project_id}/invite",
        headers=bearer(token),
        params={"user": login},
    )
    assert response.status_code == 201
    return response.json()


async def add_participant(
    client: AsyncClient,
    owner_token: str,
    project_id: int,
    login: str,
) -> dict:
    return await grant_participant(client, owner_token, project_id, login)


async def test_create_project_creates_owner_membership(
    client: AsyncClient,
    db_session: Session,
) -> None:
    token = await register_and_login(client, "ana", "ana@example.com")

    project = await create_project(client, token)

    saved_project = db_session.get(Project, project["id"])
    assert saved_project is not None
    assert saved_project.owner_id == 1

    membership = db_session.get(ProjectMember, 1)
    assert membership is not None
    assert membership.project_id == project["id"]
    assert membership.user_id == 1
    assert membership.role == "owner"


async def test_list_projects_returns_only_accessible_projects(
    client: AsyncClient,
) -> None:
    ana_token = await register_and_login(client, "ana", "ana@example.com")
    bob_token = await register_and_login(client, "bob", "bob@example.com")
    ana_project = await create_project(client, ana_token, name="Ana Project")
    await create_project(client, bob_token, name="Bob Project")

    response = await client.get("/projects", headers=bearer(ana_token))

    assert response.status_code == 200
    assert [project["id"] for project in response.json()] == [ana_project["id"]]
    assert response.json()[0]["documents"] == []


async def test_list_projects_returns_document_names_only(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(settings, "document_storage_backend", "local")
    monkeypatch.setattr(settings, "document_storage_path", str(tmp_path / "documents"))
    token = await register_and_login(client, "ana", "ana@example.com")
    project = await create_project(client, token, name="Ana Project")

    await upload_pdf(client, token, project["id"], filename="first.pdf")
    second_document = await upload_pdf(
        client,
        token,
        project["id"],
        filename="second.pdf",
    )
    await client.post(
        f"/project/{project['id']}/documents/presign-upload",
        headers=bearer(token),
        json={"filename": "pending.pdf", "content_type": "application/pdf"},
    )
    delete_response = await client.delete(
        f"/document/{second_document['id']}",
        headers=bearer(token),
    )
    assert delete_response.status_code == 204

    response = await client.get("/projects", headers=bearer(token))

    assert response.status_code == 200
    body = response.json()
    assert body == [
        {
            "id": project["id"],
            "name": "Ana Project",
            "description": "Initial description",
            "owner_id": project["owner_id"],
            "total_size_bytes": len(b"%PDF-1.7\nbody"),
            "documents_count": 1,
            "created_at": project["created_at"],
            "updated_at": body[0]["updated_at"],
            "documents": ["first.pdf"],
        }
    ]


async def test_get_project_forbids_inaccessible_project(
    client: AsyncClient,
) -> None:
    ana_token = await register_and_login(client, "ana", "ana@example.com")
    bob_token = await register_and_login(client, "bob", "bob@example.com")
    ana_project = await create_project(client, ana_token)

    response = await client.get(
        f"/project/{ana_project['id']}/info",
        headers=bearer(bob_token),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PROJECT_FORBIDDEN"


async def test_project_info_routes_read_and_patch_project(
    client: AsyncClient,
) -> None:
    token = await register_and_login(client, "owner", "owner@example.com")
    project = await create_project(client, token)

    read_response = await client.get(
        f"/project/{project['id']}/info",
        headers=bearer(token),
    )
    update_response = await client.patch(
        f"/project/{project['id']}/info",
        headers=bearer(token),
        json={"name": "Info Route Update"},
    )

    assert read_response.status_code == 200
    assert read_response.json()["id"] == project["id"]
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Info Route Update"


async def test_project_info_routes_require_authentication(
    client: AsyncClient,
) -> None:
    read_response = await client.get("/project/1/info")
    update_response = await client.patch(
        "/project/1/info",
        json={"name": "Unauthorized Update"},
    )

    assert read_response.status_code == 401
    assert read_response.json()["error"]["code"] == "MISSING_TOKEN"
    assert update_response.status_code == 401
    assert update_response.json()["error"]["code"] == "MISSING_TOKEN"


async def test_owner_and_participant_can_update_project(
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
        project["id"],
        "participant",
    )

    owner_response = await client.patch(
        f"/project/{project['id']}/info",
        headers=bearer(owner_token),
        json={"name": "Owner Update"},
    )
    participant_response = await client.patch(
        f"/project/{project['id']}/info",
        headers=bearer(participant_token),
        json={"description": None},
    )

    assert owner_response.status_code == 200
    assert owner_response.json()["name"] == "Owner Update"
    assert participant_response.status_code == 200
    assert participant_response.json()["description"] is None


async def test_only_owner_can_soft_delete_project(
    client: AsyncClient,
    db_session: Session,
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
        project["id"],
        "participant",
    )

    participant_response = await client.delete(
        f"/project/{project['id']}",
        headers=bearer(participant_token),
    )
    owner_response = await client.delete(
        f"/project/{project['id']}",
        headers=bearer(owner_token),
    )
    detail_response = await client.get(
        f"/project/{project['id']}/info",
        headers=bearer(owner_token),
    )
    list_response = await client.get("/projects", headers=bearer(owner_token))

    saved_project = db_session.get(Project, project["id"])
    assert participant_response.status_code == 403
    assert participant_response.json()["error"]["code"] == "PROJECT_FORBIDDEN"
    assert owner_response.status_code == 204
    assert detail_response.status_code == 404
    assert list_response.status_code == 200
    assert list_response.json() == []
    assert saved_project is not None
    assert saved_project.deleted_at is not None


async def test_owner_grants_participant_access_by_login(
    client: AsyncClient,
    db_session: Session,
) -> None:
    owner_token = await register_and_login(client, "owner", "owner@example.com")
    participant_token = await register_and_login(
        client,
        "participant",
        "participant@example.com",
    )
    project = await create_project(client, owner_token)

    member = await grant_participant(
        client,
        owner_token,
        project["id"],
        "participant",
    )
    detail_response = await client.get(
        f"/project/{project['id']}/info",
        headers=bearer(participant_token),
    )
    saved_member = db_session.get(ProjectMember, member["id"])

    assert member["project_id"] == project["id"]
    assert member["user_id"] == 2
    assert member["login"] == "participant"
    assert member["role"] == "participant"
    assert detail_response.status_code == 200
    assert saved_member is not None
    assert saved_member.role == "participant"


async def test_non_member_cannot_grant_or_list_members(client: AsyncClient) -> None:
    owner_token = await register_and_login(client, "owner", "owner@example.com")
    outsider_token = await register_and_login(client, "outsider", "out@example.com")
    await register_and_login(client, "third", "third@example.com")
    project = await create_project(client, owner_token)

    grant_response = await client.post(
        f"/project/{project['id']}/invite",
        headers=bearer(outsider_token),
        params={"user": "third"},
    )
    members_response = await client.get(
        f"/project/{project['id']}/members",
        headers=bearer(outsider_token),
    )

    assert grant_response.status_code == 403
    assert grant_response.json()["error"]["code"] == "PROJECT_FORBIDDEN"
    assert members_response.status_code == 403
    assert members_response.json()["error"]["code"] == "PROJECT_FORBIDDEN"


async def test_participant_cannot_grant_members(client: AsyncClient) -> None:
    owner_token = await register_and_login(client, "owner", "owner@example.com")
    participant_token = await register_and_login(
        client,
        "participant",
        "participant@example.com",
    )
    await register_and_login(client, "third", "third@example.com")
    project = await create_project(client, owner_token)
    await add_participant(
        client,
        owner_token,
        project["id"],
        "participant",
    )

    response = await client.post(
        f"/project/{project['id']}/invite",
        headers=bearer(participant_token),
        params={"user": "third"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PROJECT_FORBIDDEN"


async def test_grant_rejects_existing_member(client: AsyncClient) -> None:
    owner_token = await register_and_login(client, "owner", "owner@example.com")
    await register_and_login(client, "participant", "participant@example.com")
    project = await create_project(client, owner_token)
    await add_participant(client, owner_token, project["id"], "participant")

    response = await client.post(
        f"/project/{project['id']}/invite",
        headers=bearer(owner_token),
        params={"user": "participant"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PROJECT_MEMBER_EXISTS"


async def test_grant_rejects_unknown_login(client: AsyncClient) -> None:
    owner_token = await register_and_login(client, "owner", "owner@example.com")
    project = await create_project(client, owner_token)

    response = await client.post(
        f"/project/{project['id']}/invite",
        headers=bearer(owner_token),
        params={"user": "missing"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "USER_NOT_FOUND"


async def test_project_members_can_be_listed_by_owner_and_participant(
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
        project["id"],
        "participant",
    )

    owner_response = await client.get(
        f"/project/{project['id']}/members",
        headers=bearer(owner_token),
    )
    participant_response = await client.get(
        f"/project/{project['id']}/members",
        headers=bearer(participant_token),
    )

    assert owner_response.status_code == 200
    assert participant_response.status_code == 200
    assert [(member["login"], member["role"]) for member in owner_response.json()] == [
        ("owner", "owner"),
        ("participant", "participant"),
    ]
    assert participant_response.json() == owner_response.json()


async def test_owner_can_remove_participant(client: AsyncClient) -> None:
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
        project["id"],
        "participant",
    )

    response = await client.delete(
        f"/project/{project['id']}/members/2",
        headers=bearer(owner_token),
    )
    removed_access_response = await client.get(
        f"/project/{project['id']}/info",
        headers=bearer(participant_token),
    )

    assert response.status_code == 204
    assert removed_access_response.status_code == 403
    assert removed_access_response.json()["error"]["code"] == "PROJECT_FORBIDDEN"


async def test_participant_cannot_remove_members(client: AsyncClient) -> None:
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
        project["id"],
        "participant",
    )

    response = await client.delete(
        f"/project/{project['id']}/members/1",
        headers=bearer(participant_token),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PROJECT_FORBIDDEN"


async def test_owner_cannot_remove_owner_membership(client: AsyncClient) -> None:
    owner_token = await register_and_login(client, "owner", "owner@example.com")
    project = await create_project(client, owner_token)

    response = await client.delete(
        f"/project/{project['id']}/members/1",
        headers=bearer(owner_token),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PROJECT_FORBIDDEN"


async def test_project_member_endpoints_require_authentication(
    client: AsyncClient,
) -> None:
    invite_response = await client.post(
        "/project/1/invite",
        params={"user": "participant"},
    )
    members_response = await client.get("/project/1/members")
    delete_response = await client.delete("/project/1/members/2")

    assert invite_response.status_code == 401
    assert invite_response.json()["error"]["code"] == "MISSING_TOKEN"
    assert members_response.status_code == 401
    assert members_response.json()["error"]["code"] == "MISSING_TOKEN"
    assert delete_response.status_code == 401
    assert delete_response.json()["error"]["code"] == "MISSING_TOKEN"


async def test_projects_require_authentication_for_create_update_and_delete(
    client: AsyncClient,
) -> None:
    create_response = await client.post(
        "/project",
        json={"name": "Unauthorized Project"},
    )
    update_response = await client.patch(
        "/project/1/info",
        json={"name": "Unauthorized Update"},
    )
    delete_response = await client.delete("/project/1")

    assert create_response.status_code == 401
    assert create_response.json()["error"]["code"] == "MISSING_TOKEN"
    assert update_response.status_code == 401
    assert update_response.json()["error"]["code"] == "MISSING_TOKEN"
    assert delete_response.status_code == 401
    assert delete_response.json()["error"]["code"] == "MISSING_TOKEN"


async def test_outsider_cannot_update_or_delete_project(client: AsyncClient) -> None:
    owner_token = await register_and_login(client, "owner", "owner@example.com")
    outsider_token = await register_and_login(
        client, "outsider", "outsider@example.com"
    )
    project = await create_project(client, owner_token)

    update_response = await client.patch(
        f"/project/{project['id']}/info",
        headers=bearer(outsider_token),
        json={"name": "Hijacked"},
    )
    delete_response = await client.delete(
        f"/project/{project['id']}",
        headers=bearer(outsider_token),
    )

    assert update_response.status_code == 403
    assert update_response.json()["error"]["code"] == "PROJECT_FORBIDDEN"
    assert update_response.json()["error"]["details"] is None
    assert delete_response.status_code == 403
    assert delete_response.json()["error"]["code"] == "PROJECT_FORBIDDEN"
    assert delete_response.json()["error"]["details"] is None


async def test_projects_require_authentication(client: AsyncClient) -> None:
    response = await client.get("/projects")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "MISSING_TOKEN"


async def test_old_plural_business_routes_are_removed(
    client: AsyncClient,
) -> None:
    response = await client.post("/projects", json={"name": "Old Create"})
    project_detail = await client.get("/projects/1")
    project_documents = await client.get("/projects/1/documents")
    document_info = await client.get("/documents/1")
    invite_accept = await client.post("/invites/accept", json={"token": "token"})

    assert response.status_code == 405
    assert project_detail.status_code == 404
    assert project_documents.status_code == 404
    assert document_info.status_code == 404
    assert invite_accept.status_code == 404
