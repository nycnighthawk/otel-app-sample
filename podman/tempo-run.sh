#!/usr/bin/env bash
set -euo pipefail

# Run Tempo (traces backend)
# Usage:
#   bash podman/tempo-run.sh

NAME="${TEMPO_NAME:-tempo}"
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
  -p 3200:3200 \
  -p 4317:4317 \
  -p 4318:4318 \
  docker.io/grafana/tempo:2.6.1 \
  -config.file=/etc/tempo.yaml \
  -target=all \
  -server.http-listen-port=3200 \
  -auth.enabled=false \
  -distributor.receivers.otlp.protocols.grpc.endpoint=0.0.0.0:4317 \
  -distributor.receivers.otlp.protocols.http.endpoint=0.0.0.0:4318 \
  -storage.trace.backend=local \
  -storage.trace.local.path=/tmp/tempo

echo "[+] Tempo is running"
echo "  Ready: http://localhost:3200/ready"
