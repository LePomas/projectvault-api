#!/usr/bin/env bash
set -euo pipefail

# Reset the local PostgreSQL database to the initial bootstrap state.
#
# This removes the Docker Compose database volume. On the next db startup,
# PostgreSQL runs db/init/001_initial_schema.sql again because the data
# directory is empty.
#
# Usage:
#   ./scripts/reset-db.sh
#   ./scripts/reset-db.sh --yes --with-api

AUTO_CONFIRM="true"
WITH_API="true"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/reset-db.sh
  ./scripts/reset-db.sh --yes --with-api

Options:
  --yes, -y    Skip confirmation prompt. This is the default.
  --with-api   Start the API service after recreating the database. This is the default.
  --help, -h   Show this help message.
EOF
}

for arg in "$@"; do
  case "$arg" in
    --yes|-y)
      AUTO_CONFIRM="true"
      ;;
    --with-api)
      WITH_API="true"
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      usage >&2
      exit 2
      ;;
  esac
done

cd "$(dirname "$0")/.."

if [[ ! -f "docker-compose.yml" ]]; then
  echo "docker-compose.yml not found. Run this script from the repo checkout." >&2
  exit 1
fi

if [[ ! -f "db/init/001_initial_schema.sql" ]]; then
  echo "db/init/001_initial_schema.sql not found. Cannot restore bootstrap schema." >&2
  exit 1
fi

if [[ "$AUTO_CONFIRM" != "true" ]]; then
  echo "This will delete the local PostgreSQL Docker volume and all local data."
  echo "The database will be recreated from db/init/001_initial_schema.sql."
  read -r -p "Continue? Type 'reset' to confirm: " confirmation

  if [[ "$confirmation" != "reset" ]]; then
    echo "Cancelled."
    exit 0
  fi
fi

echo "Stopping Compose services and removing database volume..."
docker compose down --volumes --remove-orphans

echo "Starting PostgreSQL so the initial schema is applied..."
docker compose up -d db

if [[ "$WITH_API" == "true" ]]; then
  echo "Starting API service..."
  docker compose up -d --build api
fi

echo "Database reset complete."
echo "Health check after starting the API: curl http://localhost:8000/health"
