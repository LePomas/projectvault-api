# ProjectVault API

Secure project profiles and document management API.

## Implemented Stack

- Python 3.12+
- FastAPI
- PostgreSQL
- Local filesystem document storage
- MinIO-backed S3-compatible document storage for local development
- SQLAlchemy
- Docker Compose
- Pydantic v2
- JWT authentication
- S3 event handler for finalizing pending uploads
- Alembic initial schema baseline
- GitHub Actions CI for lint, format check, tests, and Compose validation
- pytest
- httpx
- Ruff

## Planned / Roadmap

- AWS S3 deployment configuration
- AWS Lambda deployment wiring
- Docker image publishing and deployment automation
- Forward database migrations beyond the initial Alembic baseline
- README deployment guide for AWS or self-hosted production

## Local development

### 1. Copy environment file

```bash
cp .env.example .env
```

### 2. Start services

```bash
docker compose up --build
```

### 3. Health check

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "projectvault-api"
}
```

### 4. API docs

Open:

```text
http://localhost:8000/docs
```

By default, uploaded documents are stored on the local filesystem under
`DOCUMENT_STORAGE_PATH`, which defaults to `storage/documents`.

Each project has a configurable storage limit through
`PROJECT_STORAGE_LIMIT_BYTES`, defaulting to `104857600` bytes.

The API also includes an S3-compatible document flow for local MinIO:

- `POST /projects/{project_id}/documents/presign-upload`
- `POST /projects/{project_id}/documents/complete-upload`
- `GET /documents/{document_id}/download-url`

To use that flow against local MinIO, set this in `.env` before starting Docker
Compose:

```env
DOCUMENT_STORAGE_BACKEND=s3
```

Docker Compose starts MinIO on `http://localhost:9000` and the MinIO console on
`http://localhost:9001`. The bucket-init container creates the configured
`S3_BUCKET` automatically. The API uses `S3_ENDPOINT_URL` inside Docker and
rewrites presigned URLs to `S3_PUBLIC_ENDPOINT_URL` for host-side clients.

Validate the local event-driven flow with:

```bash
./scripts/s3-event-smoke-test.sh
```

This script uploads to MinIO through a presigned URL, simulates an
S3-compatible object-created event, runs the event handler inside the API
container, and verifies that metadata is finalized without calling
`complete-upload`.

The event handler lives at `app.lambda_handlers.s3_events.handler`. It imports
the app code, reads object metadata through the S3 storage adapter, and updates
PostgreSQL directly. The handler is ready for AWS Lambda-style invocation, but
AWS deployment wiring remains roadmap work.

### 5. Seed sample data

Populate the Docker Compose PostgreSQL database with reusable demo data:

```bash
./scripts/seed-sample-data.sh
```

The wrapper starts the local `db` and `api` services, then runs the Python seed
script inside the API container so the Docker-only database host `db` and the
mounted document storage path match the API runtime environment.

If you intentionally want to seed from your local shell instead, use:

```bash
.venv/bin/python scripts/seed-sample-data.py
```

In that local-shell mode, the script maps the Docker-only database host `db` to
`localhost`, matching the PostgreSQL port published by Docker Compose. Your user
must also be able to write to `storage/documents`.

The script is deterministic and can be rerun. It recreates only the sample
projects, sample memberships, sample invites, and sample document files under
the `sample/projects/...` storage prefix.

Sample users all use the password `super-secret-123`:

```text
ana / ana@example.com
bob / bob@example.com
carla / carla@example.com
diego / diego@example.com
```

The script prints the current project/document IDs and the pending invite token
for `diego` after each run.

## Testing

Tests are organized by pytest marker and directory:

- `tests/unit/`: pure helper and configuration checks.
- `tests/integration/`: in-process API, database, service, script, and handler
  tests.
- `tests/e2e/`: live Docker Compose smoke wrappers.

Every test must have exactly one of `unit`, `integration`, or `e2e`; collection
fails when a test is missing a level marker or has more than one.

```bash
.venv/bin/python -m pytest -m unit
.venv/bin/python -m pytest -m integration
.venv/bin/python -m pytest -m "unit or integration"
```

E2E tests wrap the local S3 smoke scripts and are skipped by default. They require
`PROJECTVAULT_RUN_E2E=1` and an already-running S3-backed Docker Compose stack:

```bash
PROJECTVAULT_RUN_E2E=1 .venv/bin/python -m pytest -m e2e
```

## Database schema

Docker Compose initializes a fresh local PostgreSQL volume from
`db/init/001_initial_schema.sql`.

Alembic is configured with an initial baseline migration under
`alembic/versions/`. For a database that was already initialized from
`db/init/001_initial_schema.sql`, stamp the database to the initial revision
before using future migrations so Alembic does not try to replay the baseline
over existing tables.

Forward migrations after the initial baseline are not yet in place. Until the
next migration is added, keep ORM models, the bootstrap SQL, and the Alembic
baseline aligned when changing the schema.

## CI and deployment status

GitHub Actions CI is configured in `.github/workflows/ci.yml`. It installs the
Python dependencies, runs Ruff linting, Ruff format check, unit tests,
integration tests, and `docker compose config`.

Live e2e smoke tests are not part of PR CI.

CI does not currently build or publish a Docker image, deploy the API, provision
cloud infrastructure, or configure AWS services.

AWS deployment wiring remains roadmap work. The code includes an S3-compatible
storage adapter and a Lambda-style event handler, but there is no tracked
infrastructure, deployed Lambda configuration, RDS setup, production bucket
configuration, registry publishing, or production deployment workflow.

## Project structure

```text
app/
  api/              API routes
  core/             Settings and core config
  db/               Database connection setup
  models/           SQLAlchemy models
  schemas/          Pydantic schemas
  services/         Business logic
  repositories/     Database access logic
alembic/
  versions/         Alembic migration scripts
db/
  init/             PostgreSQL bootstrap SQL
tests/              Automated tests
docs/               Technical documentation
```

## Initial setup status

* [x] Repository created
* [x] Project structure created
* [x] FastAPI configured
* [x] Docker Compose configured
* [x] PostgreSQL configured
* [x] `/health` endpoint available
* [x] Initial ERD documented
* [x] API conventions documented
