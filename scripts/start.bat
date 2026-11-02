@echo off
rem Starts the server and the client without Docker (Windows).
cd /d "%~dp0server"
set STATIC_DIR=..\client\dist
py -m uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
