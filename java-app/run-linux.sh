#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="$ROOT_DIR/java-app/dist"
JAR="$DIST_DIR/shop-java.jar"

if [[ ! -f "$JAR" ]]; then
  echo "[!] Missing jar: $JAR"
  echo "    Build it: bash java-app/build-container.sh"
  exit 1
fi

export DATABASE_URL="${DATABASE_URL:-postgresql://shop:shop@localhost:5432/shop}"
export BAD_QUERY_MODE="${BAD_QUERY_MODE:-like}"
export PORT="${PORT:-8081}"

echo "[+] Running shop-java on http://localhost:$PORT"
exec java -jar "$JAR"
