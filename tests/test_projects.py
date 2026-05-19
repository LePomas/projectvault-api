import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.project import Project, ProjectMember

pytestmark = pytest.mark.anyio


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
    description: str | None = "Initial description",
) -> dict:
    response = await client.post(
        "/projects",
        headers=bearer(token),
        json={"name": name, "description": description},
    )
    assert response.status_code == 201
    return response.json()


async def invite_participant(
    client: AsyncClient,
    token: str,
    project_id: int,
    login: str,
) -> dict:
    response = await client.post(
        f"/projects/{project_id}/invites",
        headers=bearer(token),
        json={"login": login, "role": "participant"},
    )
    assert response.status_code == 201
    return response.json()


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


async def test_get_project_hides_inaccessible_project(
    client: AsyncClient,
) -> None:
    ana_token = await register_and_login(client, "ana", "ana@example.com")
    bob_token = await register_and_login(client, "bob", "bob@example.com")
    ana_project = await create_project(client, ana_token)

    response = await client.get(
        f"/projects/{ana_project['id']}",
        headers=bearer(bob_token),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROJECT_NOT_FOUND"


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
    await invite_participant(client, owner_token, project["id"], "participant")

    owner_response = await client.patch(
        f"/projects/{project['id']}",
        headers=bearer(owner_token),
        json={"name": "Owner Update"},
    )
    participant_response = await client.patch(
        f"/projects/{project['id']}",
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
    await invite_participant(client, owner_token, project["id"], "participant")

    participant_response = await client.delete(
        f"/projects/{project['id']}",
        headers=bearer(participant_token),
    )
    owner_response = await client.delete(
        f"/projects/{project['id']}",
        headers=bearer(owner_token),
    )
    detail_response = await client.get(
        f"/projects/{project['id']}",
        headers=bearer(owner_token),
    )
    list_response = await client.get("/projects", headers=bearer(owner_token))

    saved_project = db_session.get(Project, project["id"])
    assert participant_response.status_code == 404
    assert owner_response.status_code == 204
    assert detail_response.status_code == 404
    assert list_response.status_code == 200
    assert list_response.json() == []
    assert saved_project is not None
    assert saved_project.deleted_at is not None


async def test_owner_can_invite_existing_user_as_participant(
    client: AsyncClient,
    db_session: Session,
) -> None:
    owner_token = await register_and_login(client, "owner", "owner@example.com")
    await register_and_login(client, "participant", "participant@example.com")
    project = await create_project(client, owner_token)

    member = await invite_participant(client, owner_token, project["id"], "participant")

    saved_member = db_session.get(ProjectMember, member["id"])
    assert member["project_id"] == project["id"]
    assert member["user_id"] == 2
    assert member["login"] == "participant"
    assert member["role"] == "participant"
    assert saved_member is not None
    assert saved_member.project_id == project["id"]
    assert saved_member.user_id == 2
    assert saved_member.role == "participant"


async def test_participant_cannot_invite_members(client: AsyncClient) -> None:
    owner_token = await register_and_login(client, "owner", "owner@example.com")
    participant_token = await register_and_login(
        client,
        "participant",
        "participant@example.com",
    )
    await register_and_login(client, "third", "third@example.com")
    project = await create_project(client, owner_token)
    await invite_participant(client, owner_token, project["id"], "participant")

    response = await client.post(
        f"/projects/{project['id']}/invites",
        headers=bearer(participant_token),
        json={"login": "third", "role": "participant"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROJECT_NOT_FOUND"


async def test_non_member_cannot_invite_or_list_members(client: AsyncClient) -> None:
    owner_token = await register_and_login(client, "owner", "owner@example.com")
    outsider_token = await register_and_login(client, "outsider", "out@example.com")
    await register_and_login(client, "third", "third@example.com")
    project = await create_project(client, owner_token)

    invite_response = await client.post(
        f"/projects/{project['id']}/invites",
        headers=bearer(outsider_token),
        json={"login": "third", "role": "participant"},
    )
    members_response = await client.get(
        f"/projects/{project['id']}/members",
        headers=bearer(outsider_token),
    )

    assert invite_response.status_code == 404
    assert invite_response.json()["error"]["code"] == "PROJECT_NOT_FOUND"
    assert members_response.status_code == 404
    assert members_response.json()["error"]["code"] == "PROJECT_NOT_FOUND"


async def test_invite_rejects_duplicate_member(client: AsyncClient) -> None:
    owner_token = await register_and_login(client, "owner", "owner@example.com")
    await register_and_login(client, "participant", "participant@example.com")
    project = await create_project(client, owner_token)
    await invite_participant(client, owner_token, project["id"], "participant")

    response = await client.post(
        f"/projects/{project['id']}/invites",
        headers=bearer(owner_token),
        json={"login": "participant", "role": "participant"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PROJECT_MEMBER_EXISTS"


async def test_invite_rejects_unknown_login(client: AsyncClient) -> None:
    owner_token = await register_and_login(client, "owner", "owner@example.com")
    project = await create_project(client, owner_token)

    response = await client.post(
        f"/projects/{project['id']}/invites",
        headers=bearer(owner_token),
        json={"login": "missing", "role": "participant"},
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
    await invite_participant(client, owner_token, project["id"], "participant")

    owner_response = await client.get(
        f"/projects/{project['id']}/members",
        headers=bearer(owner_token),
    )
    participant_response = await client.get(
        f"/projects/{project['id']}/members",
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
    await invite_participant(client, owner_token, project["id"], "participant")

    response = await client.delete(
        f"/projects/{project['id']}/members/2",
        headers=bearer(owner_token),
    )
    removed_access_response = await client.get(
        f"/projects/{project['id']}",
        headers=bearer(participant_token),
    )

    assert response.status_code == 204
    assert removed_access_response.status_code == 404
    assert removed_access_response.json()["error"]["code"] == "PROJECT_NOT_FOUND"


async def test_participant_cannot_remove_members(client: AsyncClient) -> None:
    owner_token = await register_and_login(client, "owner", "owner@example.com")
    participant_token = await register_and_login(
        client,
        "participant",
        "participant@example.com",
    )
    project = await create_project(client, owner_token)
    await invite_participant(client, owner_token, project["id"], "participant")

    response = await client.delete(
        f"/projects/{project['id']}/members/1",
        headers=bearer(participant_token),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROJECT_NOT_FOUND"


async def test_owner_cannot_remove_owner_membership(client: AsyncClient) -> None:
    owner_token = await register_and_login(client, "owner", "owner@example.com")
    project = await create_project(client, owner_token)

    response = await client.delete(
        f"/projects/{project['id']}/members/1",
        headers=bearer(owner_token),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROJECT_NOT_FOUND"


async def test_project_member_endpoints_require_authentication(
    client: AsyncClient,
) -> None:
    invite_response = await client.post(
        "/projects/1/invites",
        json={"login": "participant", "role": "participant"},
    )
    members_response = await client.get("/projects/1/members")
    delete_response = await client.delete("/projects/1/members/2")

    assert invite_response.status_code == 401
    assert invite_response.json()["error"]["code"] == "MISSING_TOKEN"
    assert members_response.status_code == 401
    assert members_response.json()["error"]["code"] == "MISSING_TOKEN"
    assert delete_response.status_code == 401
    assert delete_response.json()["error"]["code"] == "MISSING_TOKEN"


async def test_invite_accepts_only_participant_role(client: AsyncClient) -> None:
    owner_token = await register_and_login(client, "owner", "owner@example.com")
    await register_and_login(client, "other", "other@example.com")
    project = await create_project(client, owner_token)

    response = await client.post(
        f"/projects/{project['id']}/invites",
        headers=bearer(owner_token),
        json={"login": "other", "role": "owner"},
    )

    assert response.status_code == 422


async def test_projects_require_authentication(client: AsyncClient) -> None:
    response = await client.get("/projects")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "MISSING_TOKEN"
