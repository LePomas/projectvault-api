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
- `alembic/versions/`: standard location for future Alembic migration scripts
- `db/init/001_initial_schema.sql`: PostgreSQL bootstrap schema
- `tests/`: async API tests with dependency overrides
- `docs/`: conventions, ERD notes, roadmap

Keep ORM models and `db/init/001_initial_schema.sql` aligned until a migration workflow exists. Once Alembic is configured, keep migration scripts under `alembic/versions/`.

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
.venv/bin/python -m pytest -m unit
.venv/bin/python -m pytest -m integration
.venv/bin/python -m pytest -m "unit or integration"
ruff check .
ruff format --check .
```

E2E smoke tests are opt-in and require an already-running S3-backed Docker
Compose stack:

```bash
PROJECTVAULT_RUN_E2E=1 .venv/bin/python -m pytest -m e2e
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
- Business routes use singular resource roots (`/project`, `/document`); the only
  plural route is the project list `GET /projects`. See
  [docs/API_CONVENTIONS.md](docs/API_CONVENTIONS.md) for the full list.
- Use `PATCH` for project info updates (`PATCH /project/{project_id}/info`).
- Document renames use `PUT /document/{document_id}` (there is no PATCH rename
  route). Do not reintroduce plural `/documents`/`/projects` business routes;
  `tests/integration/test_projects.py` asserts the old plural routes are gone.
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

Tests must live under `tests/unit/`, `tests/integration/`, or `tests/e2e/`.
Every test item must have exactly one of `unit`, `integration`, or `e2e`;
collection fails otherwise. E2E tests are skipped by default unless
`PROJECTVAULT_RUN_E2E=1` is set and an S3-backed Docker Compose stack is already
running.

## Sub-Agent Profiles

These are reusable prompt profiles, not tool-level agent types. When delegating,
spawn the available `explorer` or `worker` role and include the matching profile
name and focus below.

- `api-route-reviewer` (`explorer`): Review FastAPI routes for thin handlers,
  `get_current_user` on protected endpoints, registration through
  `app/api/routes.py`, plural REST resources, correct status codes, and
  `AppError` response consistency.
- `auth-security-reviewer` (`explorer`): Review password hashing, JWT settings
  and validation, auth dependencies, user identity loading, secret hygiene, and
  changes that could weaken `app/core/security.py` or protected endpoints.
- `permissions-auditor` (`explorer`): Review project and document access for
  owner/participant role enforcement, soft-delete handling, cross-user exposure,
  and service-layer permission checks before repository/database behavior.
- `db-model-sync-auditor` (`explorer`): Compare ORM model changes with
  `db/init/001_initial_schema.sql` and flag drift while there is no migration
  workflow.
- `test-coverage-worker` (`worker`): Add focused pytest coverage for changed
  behavior, especially auth, protected endpoints, permission checks,
  project/document access, status codes, and the existing `AppError` shape.
  Follow the in-memory SQLite fixture pattern.
- `service-layer-worker` (`worker`): Implement or refactor business logic in
  `app/services/`, keeping orchestration, transactions, and permission checks
  out of route handlers.
- `repository-worker` (`worker`): Own database query and persistence changes in
  `app/repositories/`, keep SQLAlchemy patterns consistent, and avoid
  route-level database logic.
- `schema-contract-reviewer` (`explorer`): Review Pydantic request and response
  schemas for validation correctness, API compatibility, naming consistency,
  and accidental data exposure.
- `ruff-style-fixer` (`worker`): Handle mechanical Python style issues from
  Ruff without broad refactors or behavior changes.
- `docs-consistency-reviewer` (`explorer`): Check README and docs updates
  against actual code behavior, especially avoiding roadmap claims from
  `docs/PROJECT_PLAN.md` as implemented facts.
- `api-regression-tester` (`worker`): Run or design endpoint-level regression
  checks around create/read/update/delete behavior, status codes, and error
  shapes.
- `config-env-reviewer` (`explorer`): Review settings and environment changes,
  including `pydantic-settings`, `.env.example`, `DATABASE_URL`, JWT config
  names, and secret hygiene.

Reviewers should return findings with file references and any checks they ran.
Workers should list changed files and verification results.

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
