#!/usr/bin/env bash
set -euo pipefail

for c in shop-python postgres; do
  if podman container exists "$c"; then
    podman rm -f "$c" >/dev/null || true
  fi
done

echo "[+] Stopped app+db containers"
