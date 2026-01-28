#!/usr/bin/env bash
set -euo pipefail

# Run the built Java jar on Linux host (no container).
# Requires:
# - Java 21+ installed (e.g., Temurin)
# - java-app/dist built using: bash java-app/build-container.sh
# - Postgres running on localhost:5432 (podman/db-run.sh)
#
# Usage:
#   bash java-app/run-linux.sh
#
# Env overrides:
#   DATABASE_URL, BAD_QUERY_MODE, PORT

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="$ROOT_DIR/java-app/dist"

JAR="$DIST_DIR/shop-java.jar"
DEPS="$DIST_DIR/deps/*"

if [[ ! -f "$JAR" ]]; then
  echo "[!] Missing jar: $JAR"
  echo "    Build it: bash java-app/build-container.sh"
  exit 1
fi

export DATABASE_URL="${DATABASE_URL:-postgresql://shop:shop@localhost:5432/shop}"
export BAD_QUERY_MODE="${BAD_QUERY_MODE:-like}"
export PORT="${PORT:-8081}"

echo "[+] Running shop-java on http://localhost:$PORT"
java -cp "$JAR:$DEPS" com.example.shop.App
