#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="$ROOT_DIR/java-app/dist"
PID_FILE="$DIST_DIR/shop-java.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "[!] No PID file at $PID_FILE (already stopped?)"
  exit 1
fi

PID="$(cat "$PID_FILE")"
if [[ -z "${PID}" ]]; then
  echo "[!] Empty PID file: $PID_FILE"
  rm -f "$PID_FILE"
  exit 1
fi

if ! kill -0 "$PID" 2>/dev/null; then
  echo "[!] Process not running (pid $PID). Removing stale pid file."
  rm -f "$PID_FILE"
  exit 0
fi

echo "[+] Stopping shop-java (pid $PID)"
kill "$PID"

# Wait up to ~10s, then SIGKILL
for _ in {1..20}; do
  if ! kill -0 "$PID" 2>/dev/null; then
    rm -f "$PID_FILE"
    echo "[+] Stopped."
    exit 0
  fi
  sleep 0.5
done

echo "[!] Still running; sending SIGKILL"
kill -9 "$PID" || true
rm -f "$PID_FILE"
echo "[+] Stopped (SIGKILL)."
