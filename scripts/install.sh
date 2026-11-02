#!/bin/sh
# Guided installation of open-fast-domotic (Linux/macOS).
#
#   sh install.sh               with Docker (recommended): .env, image, start
#   sh install.sh --no-docker   with Python: virtual environment, dependencies, .env.local
#   sh install.sh --yes         no question, take the detected values
#   sh install.sh --force       overwrite an existing .env
set -eu
cd "$(dirname "$0")"

DOCKER=1
ASSUME_YES=0
FORCE=0
for arg in "$@"; do
  case "$arg" in
    --no-docker) DOCKER=0 ;;
    --yes | -y) ASSUME_YES=1 ;;
    --force) FORCE=1 ;;
    *) echo "Unknown option: $arg"; exit 1 ;;
  esac
done

say() { printf '\n== %s\n' "$1"; }
die() { printf '\nError: %s\n' "$1" >&2; exit 1; }

# ask "question" "default" -> prints the answer
ask() {
  if [ "$ASSUME_YES" = 1 ] || [ ! -t 0 ]; then
    echo "$2"
    return
  fi
  printf '%s [%s]: ' "$1" "$2" >&2
  read -r answer
  echo "${answer:-$2}"
}

detect_dongle() {
  for port in /dev/ttyUSB* /dev/ttyACM* /dev/cu.usbserial* /dev/cu.usbmodem*; do
    [ -e "$port" ] && { echo "$port"; return; }
  done
  echo "/dev/ttyUSB0"
}

detect_timezone() {
  if [ -r /etc/timezone ]; then
    cat /etc/timezone
  elif command -v timedatectl >/dev/null 2>&1; then
    timedatectl show -p Timezone --value 2>/dev/null || echo UTC
  else
    echo UTC
  fi
}

DONGLE_DEFAULT="$(detect_dongle)"
[ -e "$DONGLE_DEFAULT" ] || echo "No dongle detected (looked for /dev/ttyUSB*, /dev/ttyACM*): is it plugged in?"

if [ "$DOCKER" = 1 ]; then
  say "Docker"
  command -v docker >/dev/null 2>&1 || die "Docker is not installed. Install it, or use: sh install.sh --no-docker"
  docker compose version >/dev/null 2>&1 || die "The 'docker compose' plugin is missing."

  say "Settings (.env)"
  if [ -f .env ] && [ "$FORCE" = 0 ]; then
    echo ".env already exists: kept (use --force to rewrite it)."
  else
    dongle="$(ask 'Dongle device' "$DONGLE_DEFAULT")"
    timezone="$(ask 'Timezone (schedules run in it)' "$(detect_timezone)")"
    printf 'Z_DONGLE_DEVICE=%s\nTZ=%s\n' "$dongle" "$timezone" > .env
    echo "Written: .env"
  fi

  say "Build and start"
  sh docker.sh up
  echo
  echo "Done. Useful commands: sh docker.sh help"
  echo "Back up your data regularly: sh docker.sh backup"
else
  say "Python"
  PYTHON=""
  for candidate in python3.13 python3.12 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 12))' 2>/dev/null; then
      PYTHON="$candidate"
      break
    fi
  done
  [ -n "$PYTHON" ] || die "Python 3.12 or newer is required."
  echo "Using $PYTHON ($("$PYTHON" --version))"

  say "Virtual environment and dependencies"
  "$PYTHON" -m venv .venv
  .venv/bin/python -m pip install --quiet --upgrade pip
  .venv/bin/python -m pip install --quiet -r server/requirements.txt
  echo "Installed in .venv"

  say "Settings (.env.local)"
  dongle=""
  if [ -f .env.local ] && [ "$FORCE" = 0 ]; then
    echo ".env.local already exists: kept (use --force to rewrite it)."
  else
    dongle="$(ask 'Dongle device' "$DONGLE_DEFAULT")"
    printf 'Z_DONGLE_PATH=%s
' "$dongle" > .env.local
    echo "Written: .env.local"
  fi
  if [ -n "$dongle" ]; then
    echo "Note: your user must be allowed to open the dongle: sudo usermod -aG dialout \$USER (then log in again)."
  fi

  say "Done"
  echo "Start it with: sh start.sh   then open http://localhost:8000"
fi
