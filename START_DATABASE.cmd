@echo off
setlocal
cd /d "%~dp0"
REM Make an automatic backup on startup, when an existing database is present.
py -3.12 -m cloud_api.backup_databases --database private
cd /d "%~dp0backend"
echo.
echo   TrueDuck Sentinel - local database
 echo   =========================
echo.
rem Prefer Python 3.12. Some Windows computers have a broken default Python alias.
py -3.12 --version >nul 2>&1
if not errorlevel 1 (
    py -3.12 server.py
    goto :end
)
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    "%LocalAppData%\Programs\Python\Python312\python.exe" server.py
    goto :end
)
py -3 --version >nul 2>&1
if not errorlevel 1 (
    py -3 server.py
    goto :end
)
echo Python could not be started.
echo Install Python 3.12 or later from https://www.python.org/downloads/
echo Or open a Command Prompt here and run: py -3.12 server.py
:end
echo.
echo If the database has stopped, press any key to close this window.
pause >nul
