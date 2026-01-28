#!/usr/bin/env bash
set -euo pipefail

# DB preparation script:
# - starts a temporary Postgres container
# - applies schema (scripts/init_db.sql)
# - seeds data (scripts/seed.py)
# - stops the temporary container
#
# Produces: a ready-to-run DB volume (podman volume).
#
# Usage:
#   bash podman/db-build.sh
#   SEED_ROWS=100000 bash podman/db-build.sh
#
# Notes:
# - This is meant for "prepare DB once" workflows.
# - Uses host python3 to run the seeder.

VOL="${PG_VOLUME:-shop_pgdata}"
TMP="${PG_TMP_NAME:-pg-shop-build}"

POSTGRES_USER="${POSTGRES_USER:-shop}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-shop}"
POSTGRES_DB="${POSTGRES_DB:-shop}"
SEED_ROWS="${SEED_ROWS:-20000}"

cd "$(dirname "$0")/.."

echo "[+] Creating volume (if needed): $VOL"
podman volume exists "$VOL" || podman volume create "$VOL" >/dev/null

if podman container exists "$TMP"; then
  echo "[!] Temporary container already exists: $TMP"
  echo "    Remove it: podman rm -f $TMP"
  exit 1
fi

echo "[+] Starting temporary Postgres for build: $TMP"
podman run -d --name "$TMP" \
  -e POSTGRES_USER="$POSTGRES_USER" \
  -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  -e POSTGRES_DB="$POSTGRES_DB" \
  -p 5433:5432 \
  -v "$VOL:/var/lib/postgresql/data" \
  -v "$(pwd)/scripts/init_db.sql:/docker-entrypoint-initdb.d/01-init_db.sql:ro" \
  docker.io/library/postgres:16-alpine

echo "[+] Waiting for Postgres to be ready..."
until podman exec "$TMP" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; do
  sleep 1
done

echo "[+] Seeding data (rows=$SEED_ROWS) ..."
export SEED_ROWS
export DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:5433/${POSTGRES_DB}"
python3 scripts/seed.py

echo "[+] Stopping temporary Postgres build container"
podman rm -f "$TMP" >/dev/null

echo "[+] DB build complete."
echo "  Volume: $VOL"
echo "  Next: bash podman/db-run.sh"
