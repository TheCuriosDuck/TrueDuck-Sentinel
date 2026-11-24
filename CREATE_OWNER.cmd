@echo off
REM Create an owner account in the SEPARATE cloud database, not your local watchlist.
REM This asks for your password in the terminal and never embeds it in source code.
cd /d "%~dp0"
py -3.12 -m cloud_api.manage_owner
pause
