#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import shutil
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath

from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.core.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.document import Document  # noqa: E402
from app.models.project import Project, ProjectInvite, ProjectMember  # noqa: E402
from app.models.user import User  # noqa: E402

DEMO_PASSWORD = "super-secret-123"
SAMPLE_STORAGE_PREFIX = "sample/projects"

PDF_BYTES = b"%PDF-1.7\n% ProjectVault sample document\n"
DOCX_BYTES = b"ProjectVault sample DOCX placeholder\n"


@dataclass(frozen=True)
class DemoUser:
    login: str
    email: str


@dataclass(frozen=True)
class DemoProject:
    key: str
    name: str
    description: str
    owner_login: str
    members: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class DemoDocument:
    project_key: str
    uploader_login: str
    filename: str
    content_type: str
    content: bytes


@dataclass(frozen=True)
class DemoInvite:
    project_key: str
    invited_login: str
    role: str
    token: str
    accepted: bool


@dataclass(frozen=True)
class SeedSummary:
    users: dict[str, int]
    projects: dict[str, int]
    documents: dict[str, int]
    pending_invites: dict[str, str]


DEMO_USERS = (
    DemoUser("ana", "ana@example.com"),
    DemoUser("bob", "bob@example.com"),
    DemoUser("carla", "carla@example.com"),
    DemoUser("diego", "diego@example.com"),
)

DEMO_PROJECTS = (
    DemoProject(
        key="alpha",
        name="Project Alpha",
        description="Contract review workspace with shared PDF and DOCX files.",
        owner_login="ana",
        members=(("ana", "owner"), ("bob", "participant")),
    ),
    DemoProject(
        key="beta",
        name="Project Beta",
        description="Implementation planning workspace owned by Bob.",
        owner_login="bob",
        members=(("bob", "owner"), ("ana", "participant"), ("carla", "participant")),
    ),
    DemoProject(
        key="gamma",
        name="Project Gamma",
        description="Private due diligence workspace for Carla.",
        owner_login="carla",
        members=(("carla", "owner"),),
    ),
)

DEMO_DOCUMENTS = (
    DemoDocument(
        project_key="alpha",
        uploader_login="ana",
        filename="alpha-contract.pdf",
        content_type="application/pdf",
        content=PDF_BYTES,
    ),
    DemoDocument(
        project_key="alpha",
        uploader_login="bob",
        filename="alpha-notes.docx",
        content_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        content=DOCX_BYTES,
    ),
    DemoDocument(
        project_key="beta",
        uploader_login="carla",
        filename="beta-brief.pdf",
        content_type="application/pdf",
        content=PDF_BYTES,
    ),
)

DEMO_INVITES = (
    DemoInvite(
        project_key="alpha",
        invited_login="bob",
        role="participant",
        token="sample-alpha-bob-accepted-token",
        accepted=True,
    ),
    DemoInvite(
        project_key="gamma",
        invited_login="diego",
        role="participant",
        token="sample-gamma-diego-pending-token",
        accepted=False,
    ),
)


def seed_sample_data(
    db: Session,
    *,
    storage_root: Path | str | None = None,
) -> SeedSummary:
    storage_path = Path(storage_root or settings.document_storage_path)

    _delete_sample_rows(db, storage_path)
    users = _upsert_users(db)
    projects = _create_projects(db, users)
    documents = _create_documents(db, storage_path, users, projects)
    pending_invites = _create_invites(db, users, projects)

    db.commit()
    return SeedSummary(
        users={login: user.id for login, user in users.items()},
        projects={key: project.id for key, project in projects.items()},
        documents={filename: document.id for filename, document in documents.items()},
        pending_invites=pending_invites,
    )


def local_database_url(database_url: str) -> str:
    url = make_url(database_url)
    if url.host == "db" and not Path("/.dockerenv").exists():
        return url.set(host="localhost").render_as_string(hide_password=False)
    return database_url


def _delete_sample_rows(db: Session, storage_path: Path) -> None:
    sample_projects = list(
        db.scalars(
            select(Project).where(
                Project.name.in_([project.name for project in DEMO_PROJECTS])
            )
        )
    )
    sample_project_ids = [project.id for project in sample_projects]

    sample_documents = list(
        db.scalars(
            select(Document).where(
                Document.storage_key.like(f"{SAMPLE_STORAGE_PREFIX}/%")
            )
        )
    )
    for document in sample_documents:
        _delete_storage_file(storage_path, document.storage_key)
        db.delete(document)

    if sample_project_ids:
        for invite in db.scalars(
            select(ProjectInvite).where(
                ProjectInvite.project_id.in_(sample_project_ids)
            )
        ):
            db.delete(invite)
        for member in db.scalars(
            select(ProjectMember).where(
                ProjectMember.project_id.in_(sample_project_ids)
            )
        ):
            db.delete(member)
        for project in sample_projects:
            db.delete(project)

    db.flush()


def _upsert_users(db: Session) -> dict[str, User]:
    users: dict[str, User] = {}
    password_hash = hash_password(DEMO_PASSWORD)

    for demo_user in DEMO_USERS:
        user = db.scalar(select(User).where(User.login == demo_user.login))
        email_owner = db.scalar(select(User).where(User.email == demo_user.email))
        if email_owner is not None and email_owner.login != demo_user.login:
            raise RuntimeError(
                f"Cannot seed {demo_user.login}: email {demo_user.email} is used by "
                f"login {email_owner.login}."
            )
        if user is None:
            user = User(
                login=demo_user.login,
                email=demo_user.email,
                password_hash=password_hash,
            )
            db.add(user)
        else:
            user.email = demo_user.email
            user.password_hash = password_hash
            user.updated_at = datetime.now(UTC)
        users[demo_user.login] = user

    db.flush()
    return users


def _create_projects(db: Session, users: dict[str, User]) -> dict[str, Project]:
    projects: dict[str, Project] = {}
    for demo_project in DEMO_PROJECTS:
        project = Project(
            name=demo_project.name,
            description=demo_project.description,
            owner_id=users[demo_project.owner_login].id,
        )
        db.add(project)
        db.flush()
        for login, role in demo_project.members:
            db.add(
                ProjectMember(project_id=project.id, user_id=users[login].id, role=role)
            )
        projects[demo_project.key] = project

    db.flush()
    return projects


def _create_documents(
    db: Session,
    storage_path: Path,
    users: dict[str, User],
    projects: dict[str, Project],
) -> dict[str, Document]:
    documents: dict[str, Document] = {}
    for demo_document in DEMO_DOCUMENTS:
        project = projects[demo_document.project_key]
        storage_key = _storage_key(project.id, demo_document.filename)
        _write_storage_file(storage_path, storage_key, demo_document.content)
        document = Document(
            project_id=project.id,
            uploaded_by_id=users[demo_document.uploader_login].id,
            filename=demo_document.filename,
            content_type=demo_document.content_type,
            size_bytes=len(demo_document.content),
            storage_key=storage_key,
            status="uploaded",
        )
        db.add(document)
        project.documents_count += 1
        project.total_size_bytes += len(demo_document.content)
        project.updated_at = datetime.now(UTC)
        documents[demo_document.filename] = document

    db.flush()
    return documents


def _create_invites(
    db: Session,
    users: dict[str, User],
    projects: dict[str, Project],
) -> dict[str, str]:
    pending_invites: dict[str, str] = {}
    now = datetime.now(UTC)
    for demo_invite in DEMO_INVITES:
        invite = ProjectInvite(
            project_id=projects[demo_invite.project_key].id,
            invited_login=demo_invite.invited_login,
            token_hash=_token_hash(demo_invite.token),
            role=demo_invite.role,
            expires_at=now + timedelta(days=7),
            accepted_at=now if demo_invite.accepted else None,
        )
        db.add(invite)
        if demo_invite.accepted:
            member_exists = any(
                login == demo_invite.invited_login
                for login, _role in next(
                    project.members
                    for project in DEMO_PROJECTS
                    if project.key == demo_invite.project_key
                )
            )
            if not member_exists:
                db.add(
                    ProjectMember(
                        project_id=projects[demo_invite.project_key].id,
                        user_id=users[demo_invite.invited_login].id,
                        role=demo_invite.role,
                    )
                )
        else:
            pending_invites[demo_invite.invited_login] = demo_invite.token

    db.flush()
    return pending_invites


def _storage_key(project_id: int, filename: str) -> str:
    return str(PurePosixPath(SAMPLE_STORAGE_PREFIX, str(project_id), filename))


def _write_storage_file(storage_path: Path, storage_key: str, content: bytes) -> None:
    path = storage_path.joinpath(*PurePosixPath(storage_key).parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _delete_storage_file(storage_path: Path, storage_key: str) -> None:
    path = storage_path.joinpath(*PurePosixPath(storage_key).parts)
    path.unlink(missing_ok=True)
    sample_root = storage_path.joinpath(*PurePosixPath(SAMPLE_STORAGE_PREFIX).parts)
    if sample_root.exists():
        for child in sample_root.iterdir():
            if child.is_dir() and not any(child.iterdir()):
                child.rmdir()
        if sample_root.exists() and not any(sample_root.iterdir()):
            shutil.rmtree(sample_root)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def main() -> None:
    database_url = local_database_url(settings.database_url)
    if database_url != settings.database_url:
        print("Using localhost for PostgreSQL because host 'db' is Docker-only.")

    engine = create_engine(database_url)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    with session_local() as db:
        summary = seed_sample_data(db)

    print("Sample data seeded.")
    print(f"Users: {summary.users}")
    print(f"Projects: {summary.projects}")
    print(f"Documents: {summary.documents}")
    if summary.pending_invites:
        print("Pending invite tokens:")
        for login, token in summary.pending_invites.items():
            print(f"  {login}: {token}")


if __name__ == "__main__":
    main()
