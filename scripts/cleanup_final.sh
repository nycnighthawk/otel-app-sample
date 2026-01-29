#!/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${SCRIPT_DIR}/.."
rm -fr .git .gitignore
cd podman
rm TESTING.md grafana-run.sh otelcol-run.sh prometheus-run.sh stack-test.sh tempo-run.sh
cd ..
rm -fr prom otel grafana
cd scripts
rm -f serve_nginx.sh
cp podman/app-run.sh podman/db-run.sh scripts/
rm -fr podman
