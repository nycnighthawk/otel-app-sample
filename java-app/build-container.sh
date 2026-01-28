#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="$ROOT_DIR/java-app"
DIST_DIR="$APP_DIR/dist"

IMAGE="${MAVEN_IMAGE:-docker.io/library/maven:3.9.9-eclipse-temurin-17}"

mkdir -p "$DIST_DIR"
rm -rf "$DIST_DIR"/*

echo "[+] Building java-app with container: $IMAGE"

podman run --rm \
  -v "$APP_DIR:/workspace:Z" \
  -w /workspace \
  "$IMAGE" \
  bash -lc 'mvn -q -DskipTests clean package'

cp "$APP_DIR/target/shop-java-1.0.0.jar" "$DIST_DIR/shop-java.jar"

echo "[+] Build complete:"
echo "  - $DIST_DIR/shop-java.jar"

