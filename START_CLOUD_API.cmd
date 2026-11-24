@echo off
REM Start the separate cloud-feed demo API on your own computer.
REM It uses a DIFFERENT database and credential from START_DATABASE.cmd.
cd /d "%~dp0"
py -3.12 -c "import fastapi, uvicorn, sqlalchemy" >nul 2>&1
if errorlevel 1 (
  echo Missing packages. In this folder run: py -3.12 -m pip install -r cloud_api\requirements.txt
  pause
  exit /b 1
)
REM Protect any existing cloud SQLite data before starting the demo.
py -3.12 -m cloud_api.backup_databases --database cloud
py -3.12 -m cloud_api.dev_server
pause
