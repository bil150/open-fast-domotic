#!/bin/sh
# Docker management for open-fast-domotic (Linux host with the dongle plugged in).
# Usage: sh docker.sh <command>
set -eu
cd "$(dirname "$0")"

VOLUME="open-fast-domotic_data"   # the compose project is named, so this does not depend on the folder
CONTAINER="open-fast-domotic-server"

usage() {
  cat <<'EOF'
Usage: sh docker.sh <command>

  up                    build the image and start (also: start)
  down                  stop and remove the container, the data is kept (also: stop)
  restart               restart the container
  status                show the container
  logs                  follow the log
  update                rebuild after replacing server/ and client/ with a newer build
  backup [file.tgz]     save the data (Zigbee network key, devices, scenes...) to a file
  restore <file.tgz>    replace the data with a backup (the file must be in this folder)
  import-network <app.db>   start from an existing Zigbee database (keeps your paired devices)
EOF
}

compose() { docker compose "$@"; }

# the .env is loaded with "required: false", which needs Docker Compose 2.24
require_compose() {
  version="$(docker compose version --short 2>/dev/null | sed 's/^v//')"
  case "$version" in
    ""|0.*|1.*|2.[0-9]|2.[0-9].*|2.1[0-9]|2.1[0-9].*|2.2[0-3]|2.2[0-3].*)
      echo "Docker Compose 2.24 or newer is required (found: ${version:-none})." >&2
      exit 1
      ;;
  esac
}

command="${1:-help}"
case "$command" in
  up|start)
    require_compose
    [ -f .env ] || echo "No .env found: using the defaults (run: sh install.sh)."
    compose up -d --build
    echo "Open http://localhost:8000"
    ;;
  down|stop) compose down ;;
  restart) compose restart ;;
  status) compose ps ;;
  logs) compose logs -f --tail=100 ;;
  update) require_compose; compose up -d --build --force-recreate ;;
  backup)
    file="${2:-ofd-backup-$(date +%Y%m%d-%H%M%S).tgz}"
    docker run --rm -v "$VOLUME":/data -v "$(pwd)":/backup alpine tar czf "/backup/$file" -C /data .
    echo "Backup written: $file"
    ;;
  restore)
    file="${2:-}"
    [ -f "$file" ] || { echo "Usage: sh docker.sh restore <file.tgz>  (the file must be in this folder)"; exit 1; }
    compose down
    docker run --rm -v "$VOLUME":/data -v "$(pwd)":/backup alpine sh -c "rm -rf /data/* && tar xzf /backup/$file -C /data"
    echo "Restored from $file. Start it with: sh docker.sh up"
    ;;
  import-network)
    file="${2:-}"
    [ -f "$file" ] || { echo "Usage: sh docker.sh import-network <app.db>"; exit 1; }
    compose up --no-start --build
    docker cp "$file" "$CONTAINER":/data/app.db
    echo "Network database imported. Start it with: sh docker.sh up"
    ;;
  help|-h|--help) usage ;;
  *) usage; exit 1 ;;
esac
