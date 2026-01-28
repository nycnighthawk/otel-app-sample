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

CONF_DIR="${CONF_DIR:-$(pwd)/.nginx}"
CONF_FILE="${CONF_FILE:-${CONF_DIR}/default.conf}"

mkdir -p "$CONF_DIR"

cat > "$CONF_FILE" <<EOF
server {
  listen ${PORT};
  listen [::]:${PORT};
  server_name _;
  root /usr/share/nginx/html;
  autoindex on;

  location / {
    try_files \$uri \$uri/ =404;
  }
}
EOF

podman rm -f "$NAME" >/dev/null 2>&1 || true

podman run -d \
  --name "$NAME" \
  --network=host \
  -v "${ARTIFACTS_DIR}:/usr/share/nginx/html:ro,Z" \
  -v "${CONF_FILE}:/etc/nginx/conf.d/default.conf:ro,Z" \
  "$IMAGE"

echo "Serving ${ARTIFACTS_DIR} at http://127.0.0.1:${PORT}/ (container: ${NAME})"
echo "Config: ${CONF_FILE}"
echo "Stop: podman stop ${NAME} && podman rm ${NAME}"

