#!/usr/bin/env bash
set -euo pipefail

NAME="${DB_NAME:-postgres}"
POSTGRES_USER="${POSTGRES_USER:-shop}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-shop}"
POSTGRES_DB="${POSTGRES_DB:-shop}"
VOL="${PG_VOLUME:-shop_pgdata}"

cd "$(dirname "$0")/.."

if podman container exists "$NAME"; then
  echo "[!] Container already exists: $NAME"
  echo "    Remove it: podman rm -f $NAME"
  exit 1
fi

podman run -d --name "$NAME" \
  --network=host \
  -e POSTGRES_USER="$POSTGRES_USER" \
  -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  -e POSTGRES_DB="$POSTGRES_DB" \
  -v "$VOL:/var/lib/postgresql/data" \
  -v "$(pwd)/scripts/init_db.sql:/docker-entrypoint-initdb.d/01-init_db.sql:ro" \
  docker.io/library/postgres:16-alpine

echo "[+] Postgres is running (host network)"
echo "  localhost:5432 db=$POSTGRES_DB user=$POSTGRES_USER"

