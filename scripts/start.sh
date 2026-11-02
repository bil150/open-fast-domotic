#!/bin/sh
# Starts the server and the client without Docker. Uses the virtual environment made by install.sh.
cd "$(dirname "$0")/server" || exit 1
PY=../.venv/bin/python
[ -x "$PY" ] || PY=python3
STATIC_DIR=../client/dist exec "$PY" -m uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
