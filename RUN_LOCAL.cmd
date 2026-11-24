@echo off
rem Run the community API for DEVELOPMENT ONLY.
cd /d "%~dp0"
start "Community API" cmd /k "py -3.12 -m cloud_api.dev_server"
echo Local community API started. Admin console: http://127.0.0.1:8877/dashboard
pause
