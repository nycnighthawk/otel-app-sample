#!/usr/bin/env bash
set -euo pipefail

# Build the FastAPI app image (Podman)
# Usage:
#   bash podman/build.sh
#   APP_IMAGE=hackathon-shop-app:dev bash podman/build.sh

APP_IMAGE="${APP_IMAGE:-hackathon-shop-app:latest}"

cd "$(dirname "$0")/.."

podman build -t "$APP_IMAGE" -f app/Dockerfile app

echo "[+] Built image: $APP_IMAGE"
