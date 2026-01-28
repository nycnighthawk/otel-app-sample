#!/usr/bin/env bash
set -euo pipefail

POD_NAME="${POD_NAME:-hackathon-otel}"

# Stop and remove containers in pod
for c in app grafana prometheus otelcol tempo postgres; do
  if podman container exists "$c"; then
    podman rm -f "$c" >/dev/null || true
  fi
done

if podman pod exists "$POD_NAME"; then
  podman pod rm -f "$POD_NAME" >/dev/null || true
fi

echo "[+] Stopped and removed pod/containers"
