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
