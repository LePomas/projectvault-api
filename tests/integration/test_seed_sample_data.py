import importlib.util
import sys
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.project import Project, ProjectMember
from app.models.user import User

pytestmark = pytest.mark.integration


def load_seed_module():
    script_path = (
        Path(__file__).resolve().parents[2] / "scripts" / "seed-sample-data.py"
    )
    spec = importlib.util.spec_from_file_location("seed_sample_data", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["seed_sample_data"] = module
    spec.loader.exec_module(module)
    return module


def test_seed_sample_data_creates_demo_dataset(
    db_session: Session,
    tmp_path: Path,
) -> None:
    seed_module = load_seed_module()

    summary = seed_module.seed_sample_data(db_session, storage_root=tmp_path)

    users = db_session.scalars(select(User).order_by(User.login)).all()
    projects = db_session.scalars(select(Project).order_by(Project.name)).all()
    documents = db_session.scalars(select(Document).order_by(Document.filename)).all()

    assert {user.login for user in users} == {"ana", "bob", "carla", "diego"}
    assert {project.name for project in projects} == {
        "Project Alpha",
        "Project Beta",
        "Project Gamma",
    }
    assert {document.filename for document in documents} == {
        "alpha-contract.pdf",
        "alpha-notes.docx",
        "beta-brief.pdf",
    }

    alpha = next(project for project in projects if project.name == "Project Alpha")
    alpha_documents = [
        document for document in documents if document.project_id == alpha.id
    ]
    assert alpha.documents_count == 2
    assert alpha.total_size_bytes == sum(
        document.size_bytes for document in alpha_documents
    )
    assert {
        (member.user_id, member.role)
        for member in db_session.scalars(
            select(ProjectMember).where(ProjectMember.project_id == alpha.id)
        )
    } == {
        (summary.users["ana"], "owner"),
        (summary.users["bob"], "participant"),
    }

    for document in documents:
        path = tmp_path.joinpath(*document.storage_key.split("/"))
        assert path.is_file()
        assert path.stat().st_size == document.size_bytes


def test_seed_sample_data_is_rerunnable_and_keeps_non_demo_rows(
    db_session: Session,
    tmp_path: Path,
) -> None:
    seed_module = load_seed_module()
    db_session.add(
        User(
            login="external",
            email="external@example.com",
            password_hash="not-a-real-hash",
        )
    )
    db_session.commit()

    first = seed_module.seed_sample_data(db_session, storage_root=tmp_path)
    second = seed_module.seed_sample_data(db_session, storage_root=tmp_path)

    assert db_session.scalar(select(User).where(User.login == "external")) is not None
    assert db_session.scalar(select(User).where(User.login == "ana")) is not None
    assert first.users.keys() == second.users.keys()
    assert db_session.scalar(select(Project).where(Project.name == "Project Alpha"))
    assert len(db_session.scalars(select(Project)).all()) == 3
    assert len(db_session.scalars(select(Document)).all()) == 3
    assert len(db_session.scalars(select(ProjectMember)).all()) == 6


def test_local_database_url_maps_compose_host_for_native_script() -> None:
    seed_module = load_seed_module()

    database_url = seed_module.local_database_url(
        "postgresql+psycopg://projectvault:projectvault@db:5432/projectvault"
    )

    assert database_url == (
        "postgresql+psycopg://projectvault:projectvault@localhost:5432/projectvault"
    )
