#!/bin/bash
set -eu

usage() {
  cat <<'EOF'
Usage:
  run_attack.sh [-c CONFIG] [-l LOG_FILE] [-e ERR_FILE] [--] [EXTRA_ARGS...]

Description:
  Launches traffic.py, redirects stdout to a log file and stderr to an error log.
  Optionally passes a config file to traffic.py.

Options:
  -c CONFIG   Path to config JSON (optional). If not provided, traffic.py uses/creates ./config.json
  -l LOG_FILE Stdout log file (default: ./traffic.out.log)
  -e ERR_FILE Stderr log file (default: ./traffic.err.log)
  -h          Show this help

Examples:
  ./run_attack.sh
  ./run_attack.sh -c config.json
  ./run_attack.sh -c config.json -l out.log -e err.log
  ./run_attack.sh -c config.json -- --some-future-arg value

Notes:
  - Script runs the python process in the foreground. Use Ctrl+C to stop.
EOF
}

CONFIG=""
OUT_LOG="./traffic.out.log"
ERR_LOG="./traffic.err.log"

while getopts "c:l:e:h" opt; do
  case "$opt" in
    c) CONFIG="$OPTARG" ;;
    l) OUT_LOG="$OPTARG" ;;
    e) ERR_LOG="$OPTARG" ;;
    h) usage; exit 0 ;;
    *) usage; exit 2 ;;
  esac
done
shift $((OPTIND - 1))

PYTHON_BIN="${PYTHON_BIN:-python3}"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
TRAFFIC_PY="$SCRIPT_DIR/attack_scan.py"

mkdir -p "$(dirname -- "$OUT_LOG")" "$(dirname -- "$ERR_LOG")"

cmd="$PYTHON_BIN $TRAFFIC_PY"
if [ -n "$CONFIG" ]; then
  cmd="$cmd --config $CONFIG"
fi

# shellcheck disable=SC2086
exec sh -c "$cmd $*" \
  1>>"$OUT_LOG" \
  2>>"$ERR_LOG"

