@echo off
rem Run local servers in separate windows for DEVELOPMENT ONLY.
cd /d "%~dp0"
start "Local indicator database" cmd /k "py -3.12 backend\server.py"
start "Community API" cmd /k "py -3.12 -m cloud_api.dev_server"
echo Local development windows started. Admin console: http://127.0.0.1:8877/dashboard
pause
