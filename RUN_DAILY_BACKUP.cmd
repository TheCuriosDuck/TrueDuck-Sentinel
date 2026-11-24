@echo off
REM Quiet wrapper for Task Scheduler. Backups are still verified by SQLite.
cd /d "%~dp0"
py -3.12 -m cloud_api.backup_databases --database both
