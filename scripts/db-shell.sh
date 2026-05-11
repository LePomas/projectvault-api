#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./scripts/db-shell.sh         -> open psql in db container
#   ./scripts/db-shell.sh bash    -> open bash in db container
#   \dt                    -- list tables
#   \d users               -- describe table
#   SELECT * FROM users;   -- query
#   \q                     -- quit psql


MODE="${1:-psql}"

if [[ "$MODE" == "bash" ]]; then
  exec docker compose exec db bash
fi

exec docker compose exec db psql -U projectvault -d projectvault
