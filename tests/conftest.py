import os
from collections.abc import AsyncGenerator, Generator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Document, Project, ProjectInvite, ProjectMember, User

TEST_TABLES = [
    User.__table__,
    Project.__table__,
    ProjectMember.__table__,
    Document.__table__,
    ProjectInvite.__table__,
]
TEST_LEVEL_MARKERS = {"unit", "integration", "e2e"}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    errors = []
    for item in items:
        selected_markers = [
            marker
            for marker in TEST_LEVEL_MARKERS
            if item.get_closest_marker(marker) is not None
        ]
        if len(selected_markers) != 1:
            markers = ", ".join(sorted(selected_markers)) or "none"
            errors.append(f"{item.nodeid}: {markers}")

    if errors:
        message = (
            "Each test must have exactly one test level marker: "
            "unit, integration, or e2e.\n"
        )
        raise pytest.UsageError(message + "\n".join(errors))


@pytest.fixture
def db_engine() -> Generator[Engine, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=TEST_TABLES)
    yield engine
    Base.metadata.drop_all(bind=engine, tables=list(reversed(TEST_TABLES)))


@pytest.fixture
def db_session(db_engine: Engine) -> Generator[Session, None, None]:
    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db_engine,
    )
    with testing_session_local() as session:
        yield session


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client(db_engine: Engine) -> AsyncGenerator[AsyncClient, None]:
    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db_engine,
    )

    async def override_get_db() -> AsyncGenerator[Session, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as test_client:
        yield test_client
    app.dependency_overrides.clear()
