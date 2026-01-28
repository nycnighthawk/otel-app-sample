#!/usr/bin/env bash
set -euo pipefail

# Run Grafana (provisioned datasources)
# Usage:
#   bash podman/grafana-run.sh

NAME="${GRAFANA_NAME:-grafana}"
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
  -p 3000:3000 \
  -e GF_SECURITY_ADMIN_USER=admin \
  -e GF_SECURITY_ADMIN_PASSWORD=admin \
  -v "$(pwd)/grafana/datasource.yaml:/etc/grafana/provisioning/datasources/ds.yaml:ro" \
  docker.io/grafana/grafana:11.2.2

echo "[+] Grafana is running"
echo "  http://localhost:3000  (admin/admin)"
