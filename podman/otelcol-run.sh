#!/usr/bin/env bash
set -euo pipefail

# Run OpenTelemetry Collector (OTLP 4317/4318, Prom scrape 8889)
# Usage:
#   bash podman/otelcol-run.sh

NAME="${OTELCOL_NAME:-otelcol}"
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
  -p 4317:4317 \
  -p 4318:4318 \
  -p 8889:8889 \
  -v "$(pwd)/otel/otel-collector.yaml:/etc/otelcol/config.yaml:ro" \
  docker.io/otel/opentelemetry-collector-contrib:0.103.0 \
  --config=/etc/otelcol/config.yaml

echo "[+] OTel Collector is running"
echo "  OTLP gRPC : localhost:4317"
echo "  OTLP HTTP : http://localhost:4318"
echo "  Metrics   : http://localhost:8889/metrics"
