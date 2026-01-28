#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="$ROOT_DIR/java-app/dist"
JAR="$DIST_DIR/shop-java.jar"
PID_FILE="$DIST_DIR/shop-java.pid"
LOG_FILE="$DIST_DIR/shop-java.log"

if [[ ! -f "$JAR" ]]; then
  echo "[!] Missing jar: $JAR"
  echo "    Build it: bash scripts/build_java.sh"
  exit 1
fi

mkdir -p "$DIST_DIR"

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "[!] Already running (pid $(cat "$PID_FILE")). Stop it: bash scripts/stop_java.sh"
  exit 1
fi

export DATABASE_URL="${DATABASE_URL:-postgresql://shop:shop@localhost:5432/shop}"
export BAD_QUERY_MODE="${BAD_QUERY_MODE:-like}"
export PORT="${PORT:-8081}"

# random_sort: make it heavy (match FastAPI shell defaults)
export BAD_RANDOM_POOL="${BAD_RANDOM_POOL:-500000}"
export BAD_RANDOM_KEY_BYTES="${BAD_RANDOM_KEY_BYTES:-10240}"

# join_bomb: bounded but slow (match FastAPI shell defaults)
export BAD_JOIN_TOP_CATS="${BAD_JOIN_TOP_CATS:-4}"
# NOTE: Java/App.java expects BAD_JOIN_MAX_ROWS_PER_CAT; map from BAD_JOIN_MAX_PER_CAT for compatibility.
export BAD_JOIN_MAX_PER_CAT="${BAD_JOIN_MAX_PER_CAT:-6144}"
export BAD_JOIN_MAX_ROWS_PER_CAT="${BAD_JOIN_MAX_ROWS_PER_CAT:-$BAD_JOIN_MAX_PER_CAT}"
export BAD_JOIN_FANOUT="${BAD_JOIN_FANOUT:-80}"

echo "[+] Starting shop-java in background on http://localhost:$PORT"
nohup java -jar "$JAR" >"$LOG_FILE" 2>&1 &
PID="$!"
echo "$PID" > "$PID_FILE"

echo "[+] Started:"
echo "  pid: $PID"
echo "  log: $LOG_FILE"

