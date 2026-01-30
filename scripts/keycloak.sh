#!/usr/bin/env bash

mkdir -p ~/keycloak/data

podman run -d --name keycloak \
  --network host \
  -e KEYCLOAK_ADMIN=admin \
  -e KEYCLOAK_ADMIN_PASSWORD=admin \
  -v ~/keycloak/data:/opt/keycloak/data \
  quay.io/keycloak/keycloak:26.5 \
  start-dev --http-port=18080 --hostname-strict=false --proxy-headers=xforwarded
