#!/usr/bin/env sh
set -eu

PORT="${PORT:-8001}"
ARTIFACTS_DIR="${ARTIFACTS_DIR:-$(pwd)/artifacts}"
IMAGE="${IMAGE:-docker.io/library/nginx:alpine}"
NAME="${NAME:-nginx-artifacts}"

if [ ! -d "$ARTIFACTS_DIR" ]; then
  echo "ERROR: artifacts directory not found: $ARTIFACTS_DIR" >&2
  exit 1
fi

# Replace any existing container with the same name
podman rm -f "$NAME" >/dev/null 2>&1 || true

exec podman run --rm \
  --name "$NAME" \
  -p "0.0.0.0:${PORT}:80" \
  -v "${ARTIFACTS_DIR}:/usr/share/nginx/html:ro,Z" \
  "$IMAGE"

