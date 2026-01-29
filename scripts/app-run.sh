#!/usr/bin/env bash
set -euo pipefail

NAME="${APP_NAME:-shop-python}"
IMAGE="${APP_IMAGE:-hackathon-shop-app:latest}"

BAD_QUERY_MODE="${BAD_QUERY_MODE:-like}"
DATABASE_URL="${DATABASE_URL:-postgresql://shop:shop@127.0.0.1:5432/shop}"

OTEL_COLLECTOR_ENDPOINT="${OTEL_COLLECTOR_ENDPOINT:-http://127.0.0.1:4318}"
OTEL_SERVICE_NAME="${OTEL_SERVICE_NAME:-shop-python}"

BAD_LIKE_MIN_COUNT="${BAD_LIKE_MIN_COUNT:-1}"
BAD_LIKE_PATTERN="${BAD_LIKE_PATTERN:-%lorem%}"

# random_sort: make it heavy
BAD_RANDOM_POOL="${BAD_RANDOM_POOL:-500000}"
BAD_RANDOM_KEY_BYTES="${BAD_RANDOM_KEY_BYTES:-10240}"

# join_bomb: bounded but slow
BAD_JOIN_TOP_CATS="${BAD_JOIN_TOP_CATS:-4}"
BAD_JOIN_MAX_PER_CAT="${BAD_JOIN_MAX_PER_CAT:-6144}"
BAD_JOIN_FANOUT="${BAD_JOIN_FANOUT:-80}"

cd "$(dirname "$0")/.."

if podman container exists "$NAME"; then
  echo "[!] Container already exists: $NAME"
  echo "    Remove it: podman rm -f $NAME"
  exit 1
fi

podman run -d --name "$NAME" \
  --network=host \
  -e DATABASE_URL="$DATABASE_URL" \
  -e BAD_QUERY_MODE="$BAD_QUERY_MODE" \
  -e BAD_LIKE_MIN_COUNT="$BAD_LIKE_MIN_COUNT" \
  -e BAD_LIKE_PATTERN="$BAD_LIKE_PATTERN" \
  -e BAD_RANDOM_POOL="$BAD_RANDOM_POOL" \
  -e BAD_RANDOM_KEY_BYTES="$BAD_RANDOM_KEY_BYTES" \
  -e BAD_JOIN_TOP_CATS="$BAD_JOIN_TOP_CATS" \
  -e BAD_JOIN_MAX_PER_CAT="$BAD_JOIN_MAX_PER_CAT" \
  -e BAD_JOIN_FANOUT="$BAD_JOIN_FANOUT" \
  -e OTEL_SERVICE_NAME="$OTEL_SERVICE_NAME" \
  -e OTEL_EXPORTER_OTLP_ENDPOINT="$OTEL_COLLECTOR_ENDPOINT" \
  -e OTEL_EXPORTER_OTLP_PROTOCOL="http/protobuf" \
  -e OTEL_TRACES_EXPORTER="otlp" \
  -e OTEL_METRICS_EXPORTER="otlp" \
  "$IMAGE"
