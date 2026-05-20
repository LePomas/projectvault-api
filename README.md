# ProjectVault API

Secure project profiles and document management API.

## Implemented Stack

- Python 3.12+
- FastAPI
- PostgreSQL
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
- Alembic migration workflow

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
  db/               Database connection and migrations
  models/           SQLAlchemy models
  schemas/          Pydantic schemas
  services/         Business logic
  repositories/     Database access logic
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
