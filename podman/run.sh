#!/usr/bin/env bash
set -euo pipefail

# Minimal Podman stack runner (no podman-compose).
# Creates a single pod with fixed ports and runs: Postgres, Tempo, OTel Collector, Prometheus, Grafana, App.

POD_NAME="${POD_NAME:-hackathon-otel}"
NETWORK_NAME="${NETWORK_NAME:-hackathon-otel-net}"

# App / DB
APP_IMAGE="${APP_IMAGE:-hackathon-shop-app:latest}"
BAD_QUERY_MODE="${BAD_QUERY_MODE:-like}"

POSTGRES_USER="${POSTGRES_USER:-shop}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-shop}"
POSTGRES_DB="${POSTGRES_DB:-shop}"

echo "[+] Creating network (if needed): $NETWORK_NAME"
podman network exists "$NETWORK_NAME" || podman network create "$NETWORK_NAME" >/dev/null

echo "[+] Building app image: $APP_IMAGE"
podman build -t "$APP_IMAGE" -f app/Dockerfile app

if podman pod exists "$POD_NAME"; then
  echo "[!] Pod already exists: $POD_NAME (remove with podman/stop.sh)"
  exit 1
fi

echo "[+] Creating pod: $POD_NAME"
podman pod create \
  --name "$POD_NAME" \
  --network "$NETWORK_NAME" \
  -p 8080:8080 \
  -p 3000:3000 \
  -p 9090:9090 \
  -p 4317:4317 \
  -p 4318:4318 \
  -p 3200:3200 \
  >/dev/null

echo "[+] Starting Postgres"
podman run -d --name postgres --pod "$POD_NAME" \
  -e POSTGRES_USER="$POSTGRES_USER" \
  -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  -e POSTGRES_DB="$POSTGRES_DB" \
  -v "$(pwd)/scripts/init_db.sql:/docker-entrypoint-initdb.d/01-init_db.sql:ro" \
  docker.io/library/postgres:16-alpine

echo "[+] Starting Tempo"
podman run -d --name tempo --pod "$POD_NAME" \
  docker.io/grafana/tempo:2.6.1 \
  -config.file=/etc/tempo.yaml \
  -target=all \
  -server.http-listen-port=3200 \
  -auth.enabled=false \
  -distributor.receivers.otlp.protocols.grpc.endpoint=0.0.0.0:4317 \
  -distributor.receivers.otlp.protocols.http.endpoint=0.0.0.0:4318 \
  -storage.trace.backend=local \
  -storage.trace.local.path=/tmp/tempo

echo "[+] Starting OTel Collector"
podman run -d --name otelcol --pod "$POD_NAME" \
  -v "$(pwd)/otel/otel-collector.yaml:/etc/otelcol/config.yaml:ro" \
  docker.io/otel/opentelemetry-collector-contrib:0.103.0 \
  --config=/etc/otelcol/config.yaml

echo "[+] Starting Prometheus"
podman run -d --name prometheus --pod "$POD_NAME" \
  -v "$(pwd)/prom/prometheus.yml:/etc/prometheus/prometheus.yml:ro" \
  docker.io/prom/prometheus:v2.54.1 \
  --config.file=/etc/prometheus/prometheus.yml

echo "[+] Starting Grafana"
podman run -d --name grafana --pod "$POD_NAME" \
  -e GF_SECURITY_ADMIN_USER=admin \
  -e GF_SECURITY_ADMIN_PASSWORD=admin \
  -v "$(pwd)/grafana/datasource.yaml:/etc/grafana/provisioning/datasources/ds.yaml:ro" \
  docker.io/grafana/grafana:11.2.2

echo "[+] Starting App (uninstrumented)"
podman run -d --name app --pod "$POD_NAME" \
  -e DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}" \
  -e BAD_QUERY_MODE="$BAD_QUERY_MODE" \
  "$APP_IMAGE"

echo
echo "[+] Stack is up"
echo "  App:        http://localhost:8080"
echo "  Grafana:    http://localhost:3000  (admin/admin)"
echo "  Prometheus: http://localhost:9090"
echo "  OTLP:       http://localhost:4318  (HTTP) / localhost:4317 (gRPC)"
echo "  Tempo:      http://localhost:3200"
echo
echo "[*] Next: seed DB: python3 scripts/seed.py"
echo "[*] Next: legit traffic: python3 scripts/legit_traffic.py"
