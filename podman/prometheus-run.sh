#!/usr/bin/env bash
set -euo pipefail

# Run Prometheus (scrapes otelcol:8889 by default)
# Usage:
#   bash podman/prometheus-run.sh

NAME="${PROM_NAME:-prometheus}"
NETWORK="${NETWORK_NAME:-hackathon-otel-net}"

cd "$(dirname "$0")/.."

podman network exists "$NETWORK" || podman network create "$NETWORK" >/dev/null

if podman container exists "$NAME"; then
  echo "[!] Container already exists: $NAME"
  echo "    Remove it: podman rm -f $NAME"
  exit 1
fi

podman run -d --name "$NAME" \
  --network "$NETWORK" \
  -p 9090:9090 \
  -v "$(pwd)/prom/prometheus.yml:/etc/prometheus/prometheus.yml:ro" \
  docker.io/prom/prometheus:v2.54.1 \
  --config.file=/etc/prometheus/prometheus.yml

echo "[+] Prometheus is running"
echo "  UI: http://localhost:9090"
