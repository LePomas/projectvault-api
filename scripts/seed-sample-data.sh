#!/usr/bin/env bash
set -euo pipefail

# Seed the local Docker Compose PostgreSQL database from inside the API
# container so DATABASE_URL=db and DOCUMENT_STORAGE_PATH=/app/storage/documents
# match the runtime environment.

cd "$(dirname "$0")/.."

if [[ ! -f "docker-compose.yml" ]]; then
  echo "docker-compose.yml not found. Run this script from the repo checkout." >&2
  exit 1
fi

echo "Starting local services..."
docker compose up -d db api

echo "Seeding sample data inside the API container..."
docker compose exec api python scripts/seed-sample-data.py
