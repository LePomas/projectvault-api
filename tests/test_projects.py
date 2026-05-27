from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.project import Project, ProjectInvite, ProjectMember

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


async def accept_invite(
    client: AsyncClient,
    token: str,
    invite_token: str,
) -> dict:
    response = await client.post(
        "/invites/accept",
        headers=bearer(token),
        json={"token": invite_token},
    )
    assert response.status_code == 201
    return response.json()


async def add_participant(
    client: AsyncClient,
    owner_token: str,
    participant_token: str,
    project_id: int,
    login: str,
) -> dict:
    invite = await invite_participant(client, owner_token, project_id, login)
    return await accept_invite(client, participant_token, invite["token"])


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
    await add_participant(
        client,
        owner_token,
        participant_token,
        project["id"],
        "participant",
    )

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
    await add_participant(
        client,
        owner_token,
        participant_token,
        project["id"],
        "participant",
    )

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


async def test_owner_can_create_pending_invite_for_existing_user(
    client: AsyncClient,
    db_session: Session,
) -> None:
    owner_token = await register_and_login(client, "owner", "owner@example.com")
    await register_and_login(client, "participant", "participant@example.com")
    project = await create_project(client, owner_token)

    invite = await invite_participant(client, owner_token, project["id"], "participant")

    saved_invite = db_session.get(ProjectInvite, invite["id"])
    assert invite["project_id"] == project["id"]
    assert invite["invited_login"] == "participant"
    assert invite["role"] == "participant"
    assert invite["token"]
    assert saved_invite is not None
    assert saved_invite.project_id == project["id"]
    assert saved_invite.invited_login == "participant"
    assert saved_invite.accepted_at is None
    assert saved_invite.token_hash != invite["token"]
    assert db_session.get(ProjectMember, 2) is None


async def test_invited_user_can_accept_invite_and_access_project(
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
    invite = await invite_participant(client, owner_token, project["id"], "participant")

    member = await accept_invite(client, participant_token, invite["token"])
    detail_response = await client.get(
        f"/projects/{project['id']}",
        headers=bearer(participant_token),
    )

    assert member["project_id"] == project["id"]
    assert member["user_id"] == 2
    assert member["login"] == "participant"
    assert member["role"] == "participant"
    assert detail_response.status_code == 200
    saved_invite = db_session.get(ProjectInvite, invite["id"])
    assert saved_invite is not None
    assert saved_invite.accepted_at is not None


async def test_owner_can_invite_another_owner(client: AsyncClient) -> None:
    owner_token = await register_and_login(client, "owner", "owner@example.com")
    second_owner_token = await register_and_login(
        client,
        "second_owner",
        "second-owner@example.com",
    )
    project = await create_project(client, owner_token)

    response = await client.post(
        f"/projects/{project['id']}/invites",
        headers=bearer(owner_token),
        json={"login": "second_owner", "role": "owner"},
    )
    assert response.status_code == 201
    assert response.json()["role"] == "owner"

    member = await accept_invite(
        client,
        second_owner_token,
        response.json()["token"],
    )
    assert member["role"] == "owner"

    delete_response = await client.delete(
        f"/projects/{project['id']}",
        headers=bearer(second_owner_token),
    )
    assert delete_response.status_code == 204


async def test_uninvited_user_cannot_accept_invite(client: AsyncClient) -> None:
    owner_token = await register_and_login(client, "owner", "owner@example.com")
    await register_and_login(client, "participant", "participant@example.com")
    outsider_token = await register_and_login(client, "outsider", "out@example.com")
    project = await create_project(client, owner_token)
    invite = await invite_participant(client, owner_token, project["id"], "participant")

    response = await client.post(
        "/invites/accept",
        headers=bearer(outsider_token),
        json={"token": invite["token"]},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROJECT_INVITE_NOT_FOUND"


async def test_accept_rejects_invalid_token(client: AsyncClient) -> None:
    participant_token = await register_and_login(
        client,
        "participant",
        "participant@example.com",
    )

    response = await client.post(
        "/invites/accept",
        headers=bearer(participant_token),
        json={"token": "invalid-token"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROJECT_INVITE_NOT_FOUND"


async def test_accept_rejects_expired_invite(
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
    invite = await invite_participant(client, owner_token, project["id"], "participant")
    saved_invite = db_session.get(ProjectInvite, invite["id"])
    assert saved_invite is not None
    saved_invite.expires_at = datetime.now(UTC) - timedelta(days=1)
    db_session.commit()

    response = await client.post(
        "/invites/accept",
        headers=bearer(participant_token),
        json={"token": invite["token"]},
    )

    assert response.status_code == 410
    assert response.json()["error"]["code"] == "PROJECT_INVITE_EXPIRED"


async def test_accept_rejects_already_accepted_invite(client: AsyncClient) -> None:
    owner_token = await register_and_login(client, "owner", "owner@example.com")
    participant_token = await register_and_login(
        client,
        "participant",
        "participant@example.com",
    )
    project = await create_project(client, owner_token)
    invite = await invite_participant(client, owner_token, project["id"], "participant")
    await accept_invite(client, participant_token, invite["token"])

    response = await client.post(
        "/invites/accept",
        headers=bearer(participant_token),
        json={"token": invite["token"]},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PROJECT_INVITE_ACCEPTED"


async def test_participant_cannot_invite_members(client: AsyncClient) -> None:
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
        participant_token,
        project["id"],
        "participant",
    )

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


async def test_invite_rejects_duplicate_pending_invite(client: AsyncClient) -> None:
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
    assert response.json()["error"]["code"] == "PROJECT_INVITE_EXISTS"


async def test_invite_rejects_existing_member(client: AsyncClient) -> None:
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
    await add_participant(
        client,
        owner_token,
        participant_token,
        project["id"],
        "participant",
    )

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
    await add_participant(
        client,
        owner_token,
        participant_token,
        project["id"],
        "participant",
    )

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
    await add_participant(
        client,
        owner_token,
        participant_token,
        project["id"],
        "participant",
    )

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
    accept_response = await client.post(
        "/invites/accept",
        json={"token": "token"},
    )

    assert invite_response.status_code == 401
    assert invite_response.json()["error"]["code"] == "MISSING_TOKEN"
    assert members_response.status_code == 401
    assert members_response.json()["error"]["code"] == "MISSING_TOKEN"
    assert delete_response.status_code == 401
    assert delete_response.json()["error"]["code"] == "MISSING_TOKEN"
    assert accept_response.status_code == 401
    assert accept_response.json()["error"]["code"] == "MISSING_TOKEN"


async def test_projects_require_authentication_for_create_update_and_delete(
    client: AsyncClient,
) -> None:
    create_response = await client.post(
        "/projects",
        json={"name": "Unauthorized Project"},
    )
    update_response = await client.patch(
        "/projects/1",
        json={"name": "Unauthorized Update"},
    )
    delete_response = await client.delete("/projects/1")

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
        f"/projects/{project['id']}",
        headers=bearer(outsider_token),
        json={"name": "Hijacked"},
    )
    delete_response = await client.delete(
        f"/projects/{project['id']}",
        headers=bearer(outsider_token),
    )

    assert update_response.status_code == 404
    assert update_response.json()["error"]["code"] == "PROJECT_NOT_FOUND"
    assert update_response.json()["error"]["details"] is None
    assert delete_response.status_code == 404
    assert delete_response.json()["error"]["code"] == "PROJECT_NOT_FOUND"
    assert delete_response.json()["error"]["details"] is None


async def test_invite_rejects_unsupported_role(client: AsyncClient) -> None:
    owner_token = await register_and_login(client, "owner", "owner@example.com")
    await register_and_login(client, "other", "other@example.com")
    project = await create_project(client, owner_token)

    response = await client.post(
        f"/projects/{project['id']}/invites",
        headers=bearer(owner_token),
        json={"login": "other", "role": "admin"},
    )

    assert response.status_code == 422


async def test_projects_require_authentication(client: AsyncClient) -> None:
    response = await client.get("/projects")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "MISSING_TOKEN"
