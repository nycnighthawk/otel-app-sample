#!/usr/bin/env bash
podman volume create gitea-data

IPA="$(ip route get 1.1.1.1 | awk '{for(i=1;i<=NF;i++) if ($i=="src") {print $(i+1); exit}}')"
podman run -d --name gitea \
  --network host \
  -e GITEA__server__HTTP_PORT=13001 \
  -v gitea-data:/data \
  docker.io/gitea/gitea:1.25
