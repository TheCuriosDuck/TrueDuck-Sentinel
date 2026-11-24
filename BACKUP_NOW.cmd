@echo off
REM Save private AND cloud SQLite backups into %%LOCALAPPDATA%%\TrueDuck Sentinel\Backups.
REM This location survives deleting the old version's folder.
cd /d "%~dp0"
py -3.12 -m cloud_api.backup_databases --database both
pause
