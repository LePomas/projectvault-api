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
    db_session: Session,
) -> None:
    owner_token = await register_and_login(client, "owner", "owner@example.com")
    participant_token = await register_and_login(
        client,
        "participant",
        "participant@example.com",
    )
    project = await create_project(client, owner_token)
    db_session.add(
        ProjectMember(
            project_id=project["id"],
            user_id=2,
            role="participant",
        )
    )
    db_session.commit()

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
    db_session.add(
        ProjectMember(
            project_id=project["id"],
            user_id=2,
            role="participant",
        )
    )
    db_session.commit()

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


async def test_projects_require_authentication(client: AsyncClient) -> None:
    response = await client.get("/projects")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "MISSING_TOKEN"
