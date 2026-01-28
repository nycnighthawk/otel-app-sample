#!/usr/bin/env bash
set -euo pipefail

# Build the Java app using a containerized Maven build.
# - Mounts the source into the container
# - Produces:
#   - java-app/dist/shop-java.jar
#   - java-app/dist/deps/*  (runtime dependencies)
#
# Usage:
#   bash java-app/build-container.sh
#
# Notes:
# - Uses official OSS image from Docker Hub: docker.io/library/maven
# - Does not require Maven installed on the host.

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="$ROOT_DIR/java-app"
DIST_DIR="$APP_DIR/dist"

IMAGE="${MAVEN_IMAGE:-docker.io/library/maven:3.9.9-eclipse-temurin-21}"

mkdir -p "$DIST_DIR"
rm -rf "$DIST_DIR"/*

echo "[+] Building java-app with container: $IMAGE"

podman run --rm \
  -v "$APP_DIR:/workspace:Z" \
  -w /workspace \
  "$IMAGE" \
  bash -lc 'mvn -q -DskipTests package'

# Copy artifacts out of the mounted workspace into a clean dist/ folder
cp "$APP_DIR/target/shop-java-1.0.0.jar" "$DIST_DIR/shop-java.jar"
mkdir -p "$DIST_DIR/deps"
cp -r "$APP_DIR/target/deps/." "$DIST_DIR/deps/"

echo "[+] Build complete:"
echo "  - $DIST_DIR/shop-java.jar"
echo "  - $DIST_DIR/deps/"

