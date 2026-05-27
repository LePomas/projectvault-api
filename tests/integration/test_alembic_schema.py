import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_alembic_initial_schema_renders_current_postgresql_baseline() -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = "postgresql+psycopg://projectvault:projectvault@localhost/db"

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )

    rendered_sql = result.stdout + result.stderr

    assert result.returncode == 0, rendered_sql
    assert "CREATE TABLE users" in rendered_sql
    assert "CREATE TABLE projects" in rendered_sql
    assert "CREATE TABLE project_members" in rendered_sql
    assert "CREATE TABLE documents" in rendered_sql
    assert "CREATE TABLE project_invites" in rendered_sql
    assert "invited_login VARCHAR(50)" in rendered_sql
    assert "invited_email VARCHAR(255)" in rendered_sql
    assert "token_hash TEXT NOT NULL" in rendered_sql
    assert "CREATE INDEX idx_documents_status" in rendered_sql
    assert "CREATE TABLE user (" not in rendered_sql
    assert "CREATE TABLE project (" not in rendered_sql
    assert "CREATE TABLE project_member (" not in rendered_sql
    assert "CREATE TABLE document (" not in rendered_sql
    assert "CREATE TABLE project_invite (" not in rendered_sql
    assert "token VARCHAR(255)" not in rendered_sql
