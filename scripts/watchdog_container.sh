cat >~/podman-watchdog-bootstrap.sh <<'EOF'
#!/bin/sh
set -eu

# Rootless container names to keep running (space-separated)
CONTAINERS="nginx-artifacts"

WATCHDOG="$HOME/.local/bin/podman-ensure-containers.sh"
CRON_LINE='*/2 * * * * PATH=/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin $HOME/.local/bin/podman-ensure-containers.sh'

log() { printf '%s\n' "$*" >&2; }

enable_linger_once() {
  command -v loginctl >/dev/null 2>&1 || { log "loginctl not found; skipping linger"; return 0; }

  if loginctl show-user "$USER" -p Linger 2>/dev/null | grep -q 'Linger=yes'; then
    log "linger already enabled for $USER"
    return 0
  fi

  command -v sudo >/dev/null 2>&1 || { log "sudo not found; cannot enable linger"; exit 1; }
  log "enabling linger for $USER (requires sudo)"
  sudo loginctl enable-linger "$USER"
}

install_watchdog() {
  mkdir -p "$(dirname "$WATCHDOG")"
  tmp="$(mktemp)"

  cat > "$tmp" <<EOF2
#!/bin/sh
set -eu

CONTAINERS="nginx-artifacts keycloak gitea postgres shop-python"

log() { logger -t podman-ensure "$*"; }

for c in $CONTAINERS; do
  if ! podman container exists "$c" >/dev/null 2>&1; then
    # Container does not exist; do nothing
    continue
  fi

  if podman inspect -f '{{.State.Running}}' "$c" 2>/dev/null | grep -qx true; then
    continue
  fi

  state="$(podman inspect -f '{{.State.Status}}' "$c" 2>/dev/null || echo unknown)"
  case "$state" in
    created|configured|exited|stopped)
      log "starting container '$c' (state=$state)"
      podman start "$c" >/dev/null 2>&1 || log "FAILED to start '$c'"
      ;;
    paused)
      log "unpausing container '$c'"
      podman unpause "$c" >/dev/null 2>&1 || log "FAILED to unpause '$c'"
      ;;
    running)
      ;;
    *)
      log "container '$c' in unexpected state '$state'; trying restart"
      podman restart "$c" >/dev/null 2>&1 || podman start "$c" >/dev/null 2>&1 || log "FAILED to restart/start '$c'"
      ;;
  esac
done
EOF2

  chmod 0755 "$tmp"

  if [ -f "$WATCHDOG" ] && cmp -s "$tmp" "$WATCHDOG"; then
    rm -f "$tmp"
    log "watchdog already up to date: $WATCHDOG"
  else
    mv "$tmp" "$WATCHDOG"
    log "installed watchdog: $WATCHDOG"
  fi
}

install_cron() {
  ( crontab -l 2>/dev/null | grep -Fvx "$CRON_LINE" || true; echo "$CRON_LINE" ) | crontab -
  log "cron ensured: $CRON_LINE"
}

enable_linger_once
install_watchdog
install_cron
log "done"
EOF

chmod 0755 ~/podman-watchdog-bootstrap.sh
