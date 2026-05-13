# ProjectVault API Agent Guide

## Purpose

ProjectVault API is a Python 3.12+ FastAPI backend for secure project profiles and document management.

The codebase is the source of truth. `docs/PROJECT_PLAN.md` is roadmap context only; do not treat planned phases, cloud features, CI/CD, deployment, or optional features as implemented unless the code shows they exist or the user explicitly asks to build them.

## Current Stack

- FastAPI, Pydantic v2, SQLAlchemy 2.x
- PostgreSQL in Docker Compose; SQLite in-memory for current tests
- JWT authentication
- pytest, httpx, Ruff

Do not add a new framework, package manager, CI system, deployment tool, or migration workflow without explicit approval.

## Repository Map

- `app/main.py`: app setup and exception handler registration
- `app/api/`: routes and dependencies
- `app/core/`: settings, security, shared exceptions
- `app/db/`: SQLAlchemy base/session setup
- `app/models/`: ORM models
- `app/schemas/`: Pydantic schemas
- `app/services/`: business rules, permissions, transactions
- `app/repositories/`: database access helpers
- `db/init/001_initial_schema.sql`: PostgreSQL bootstrap schema
- `tests/`: async API tests with dependency overrides
- `docs/`: conventions, ERD notes, roadmap

Keep ORM models and `db/init/001_initial_schema.sql` aligned until a migration workflow exists.

## Commands

Local run:

```bash
cp .env.example .env
docker compose up --build
curl http://localhost:8000/health
```

API docs: `http://localhost:8000/docs`

Database shell:

```bash
./scripts/db-shell.sh
./scripts/db-shell.sh bash
```

Tests and checks, when dependencies are installed:

```bash
pytest
ruff check .
ruff format --check .
```

Only run `ruff format .` when formatting changes are intended.

## Coding Rules

- Target Python 3.12 and Ruff style: line length 88, target `py312`, lint rules `E`, `F`, `I`, `B`, `UP`.
- Use Pydantic schemas for request/response validation.
- Use typed SQLAlchemy models with `Mapped[...]` and `mapped_column`.
- Keep route handlers thin: validate input, load dependencies, call services, return schemas.
- Put business rules, permission checks, transactions, and orchestration in services.
- Put database query and persistence logic in repositories.
- Do not bypass repositories for non-trivial database behavior unless nearby code already does so.

## API Rules

- Register route modules through `app/api/routes.py`.
- Use plural REST resources such as `/projects` and `/documents`.
- Use `PATCH` for partial updates.
- Do not use `GET` for state-changing actions.
- Protected endpoints must depend on `get_current_user`.
- Successful creates return `201`; reads and updates `200`; deletes `204`.
- JSON is the default response format except file downloads.

Use the existing `AppError` response shape:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message.",
    "details": null
  }
}
```

## Security And Permissions

- Never store plaintext passwords; use `app/core/security.py`.
- Do not weaken password hashing, JWT validation, or auth dependencies.
- JWT settings come from `app/core/config.py`.
- Do not expose projects or documents without checking project access.
- Preserve `owner` and `participant` roles unless schema, services, and tests are deliberately updated together.
- Existing project deletes are soft deletes via `projects.deleted_at`.

## Testing

Add or update tests for behavior changes, especially auth, protected endpoints, permission checks, project/document access, and error responses.

Keep tests isolated from the developer database. Follow the current in-memory SQLite fixture pattern unless a test explicitly needs PostgreSQL behavior.

## Environment

- Settings use `pydantic-settings` and environment variables.
- `.env` and local override files are ignored; do not commit secrets.
- `.env.example` is the tracked source for local variable names.
- Required runtime configuration includes `DATABASE_URL`.
- JWT settings are configurable through `JWT_SECRET_KEY`, `JWT_ALGORITHM`, and `JWT_EXPIRE_MINUTES`.

## Done Criteria

- Relevant tests pass, or the final response explains why they were not run.
- `ruff check .` passes for Python changes, or the remaining issue is reported.
- API behavior remains consistent with `docs/API_CONVENTIONS.md`.
- README/docs are updated when setup, API behavior, architecture, or configuration changes.
- Database model changes are reflected in the bootstrap SQL or migration mechanism.
- The diff stays limited to the requested scope.

## Do Not

- Do not treat `docs/PROJECT_PLAN.md` roadmap items as implemented.
- Do not invent Makefile, CI, deployment, migration, or dependency commands that are not present.
- Do not modify application code when the request is only to update project guidance.
- Do not commit `.env`, `.venv`, caches, `__pycache__`, or generated local artifacts.
- Do not introduce S3, Lambda, CI/CD, Alembic migrations, or deployment work unless explicitly requested.
