# ProjectVault API Agent Guide

## Project Overview

ProjectVault API is a Python 3.12+ FastAPI backend for secure project profiles and document management. The stable stack in this repository is FastAPI, Pydantic v2, SQLAlchemy 2.x, PostgreSQL, Docker Compose, JWT authentication, pytest, httpx, and Ruff.

Use `docs/PROJECT_PLAN.md` only for project direction. Do not treat roadmap phases, dates, or optional features as already implemented.

## Repository Layout

- `app/main.py` creates the FastAPI app, registers the shared `AppError` handler, and includes the root API router.
- `app/api/` contains route modules and dependencies.
- `app/core/` contains settings, security helpers, and shared exceptions.
- `app/db/` contains SQLAlchemy base/session setup.
- `app/models/` contains SQLAlchemy ORM models.
- `app/schemas/` contains Pydantic request/response schemas.
- `app/services/` contains business logic and permission decisions.
- `app/repositories/` contains database query and persistence helpers.
- `db/init/001_initial_schema.sql` bootstraps PostgreSQL on first container volume creation.
- `tests/` contains async API tests using `httpx.AsyncClient` and an in-memory SQLite database.
- `docs/` contains API conventions, ERD notes, and the project plan.

There is currently no Makefile, requirements file, lockfile, Alembic directory, or CI config in the tracked repository.

## Setup And Run Commands

Use the commands documented by the repo:

```bash
cp .env.example .env
docker compose up --build
curl http://localhost:8000/health
```

The API docs are served locally at:

```text
http://localhost:8000/docs
```

The Dockerfile installs runtime dependencies with:

```bash
uv pip install --system -r pyproject.toml
```

Use `./scripts/db-shell.sh` to open `psql` in the Compose `db` container, or `./scripts/db-shell.sh bash` to open a shell in that container.

## Test, Lint, And Format Commands

`pyproject.toml` configures pytest and Ruff. When the project dependencies are installed, use:

```bash
pytest
ruff check .
ruff format --check .
ruff format .
```

Only run `ruff format .` when formatting changes are intended. There is no configured mypy command in this repo.

## Coding Conventions

- Target Python 3.12 and keep Ruff-compatible style: line length 88, target `py312`, lint rules `E`, `F`, `I`, `B`, and `UP`.
- Keep imports sorted according to Ruff.
- Use Pydantic schemas for request and response validation.
- Use SQLAlchemy ORM models with typed `Mapped[...]` fields and `mapped_column`.
- Use the existing `AppError` pattern for application errors:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message.",
    "details": null
  }
}
```

- Never store plaintext passwords. Use the helpers in `app/core/security.py`.
- JWT settings come from `app/core/config.py`; the current default expiration is 60 minutes.

## Architecture Conventions

- Keep the existing layered structure: routes, dependencies, services, repositories, models, schemas, core, and db.
- Route handlers should receive requests, validate schemas, load dependencies, call services, and return response schemas.
- Services should hold business rules, permission checks, transactions, and coordination between repositories.
- Repositories should encapsulate database access and avoid heavy business logic.
- Do not put new business logic directly in route handlers when it belongs in a service.
- Do not bypass repositories for non-trivial database behavior unless the surrounding code already does so for that case.

## FastAPI Conventions

- Add routes through `app/api/routes.py` by including module routers.
- Use plural REST resource names such as `/projects` and `/documents`.
- Use `PATCH` for partial updates.
- Do not use `GET` for actions that create or modify state.
- Protected endpoints should depend on `get_current_user`.
- Successful creates should return `201`; reads and updates `200`; deletes `204`.
- JSON is the default response format except file downloads.

## Database Rules

- PostgreSQL is the local Compose database; tests currently use SQLite in memory.
- Keep SQLAlchemy models and `db/init/001_initial_schema.sql` aligned until an Alembic migration workflow exists.
- The bootstrap SQL only runs automatically when the Postgres data volume is empty.
- Existing project deletes are soft deletes via `projects.deleted_at`.
- Preserve the `owner` and `participant` project roles unless the schema and tests are deliberately updated together.

## Testing Expectations

- Add or update tests for behavior changes, especially auth, protected endpoints, permissions, project access, and error responses.
- Tests use `pytest.mark.anyio`, `httpx.AsyncClient`, and dependency overrides for `get_db`.
- Keep tests isolated from the developer database; follow the current in-memory SQLite fixture pattern unless a test explicitly needs PostgreSQL behavior.
- Verify authentication failures include the expected error code and HTTP status.

## Environment And Configuration

- Settings are loaded with `pydantic-settings` from environment variables and `.env`.
- `.env` and local override files are ignored; keep secrets out of git.
- `.env.example` is the tracked source for local environment variable names.
- Required runtime configuration includes `DATABASE_URL`; JWT settings are configurable by `JWT_SECRET_KEY`, `JWT_ALGORITHM`, and `JWT_EXPIRE_MINUTES`.
- The default local JWT secret is for development only.

## Definition Of Done

- Relevant tests pass locally, or the final response states exactly why they were not run.
- Ruff check passes for Python changes, or the final response states the remaining lint issue.
- API behavior remains consistent with `docs/API_CONVENTIONS.md`.
- README or docs are updated when setup, API behavior, or architecture changes.
- Database model changes are reflected in the current database bootstrap or migration mechanism.
- The final diff is limited to the requested scope.

## Things Codex Must Not Do

- Do not implement roadmap items from `docs/PROJECT_PLAN.md` unless the user explicitly asks for them.
- Do not invent Makefile, CI, migration, deployment, or dependency commands that are not present in the repo.
- Do not modify application code while only updating project guidance.
- Do not commit `.env`, `.venv`, caches, `__pycache__`, or generated local artifacts.
- Do not change the primary stack or introduce new frameworks without explicit user approval.
- Do not expose documents or project data without checking project access.
- Do not weaken authentication, password hashing, JWT validation, or project permission checks.
