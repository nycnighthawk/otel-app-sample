#!/usr/bin/env bash
set -euo pipefail

# Basic smoke test for the Linux VM once components are running.
# Usage:
#   bash podman/stack-test.sh

APP_BASE="${APP_BASE:-http://localhost:8080}"
JAVA_BASE="${JAVA_BASE:-http://localhost:8081}"

echo "[*] Testing Python app..."
curl -fsS "$APP_BASE/api/health" | cat; echo
curl -fsS "$APP_BASE/api/products?limit=3" | head -c 200; echo; echo
curl -fsS "$APP_BASE/api/bad" | cat; echo

echo "[*] Testing Prometheus..."
curl -fsS "http://localhost:9090/-/ready" | cat; echo

echo "[*] Testing Grafana..."
curl -fsS "http://localhost:3000/api/health" | cat; echo

echo "[*] Testing OTel Collector metrics endpoint..."
curl -fsS "http://localhost:8889/metrics" | head -n 5

echo "[*] Testing Java app (if running)..."
curl -fsS "$JAVA_BASE/api/health" | cat; echo
