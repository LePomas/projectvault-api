# ProjectVault API

Secure project profiles and document management API.

## Implemented Stack

- Python 3.12+
- FastAPI
- PostgreSQL
- MinIO for local S3-compatible document storage
- SQLAlchemy
- Docker Compose
- Pydantic v2
- JWT authentication
- pytest
- httpx
- Ruff

## Planned / Roadmap

- AWS S3
- AWS Lambda
- GitHub Actions / GitLab CI
- Alembic migration workflow using `alembic/versions/`

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

Uploaded documents are stored locally under `DOCUMENT_STORAGE_PATH`, which
defaults to `storage/documents` for local development.

Each project has a configurable storage limit through
`PROJECT_STORAGE_LIMIT_BYTES`, defaulting to `104857600` bytes.

To use the Phase 5 S3-compatible document flow against local MinIO, set this in
`.env` before starting Docker Compose:

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

This script uploads to MinIO through a presigned URL, simulates an S3
object-created event, runs the Lambda handler inside the API container, and
verifies that metadata is finalized without calling `complete-upload`.

AWS S3 object-created events can be processed by the Lambda handler at
`app.lambda_handlers.s3_events.handler`. The handler imports the app code,
reads object metadata through the S3 storage adapter, and updates PostgreSQL
directly. Configure the Lambda environment with `DATABASE_URL`,
`DOCUMENT_STORAGE_BACKEND=s3`, `S3_BUCKET`, `S3_REGION`, and credentials or an
IAM role that can read/delete objects from the bucket.

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
  versions/         Future Alembic migration scripts
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
