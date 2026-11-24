@echo off
REM Publish ONLY opted-in, approved domains/URLs from your private database.
REM This sends a snapshot to the LOCAL demonstration API, never to the internet.
cd /d "%~dp0"
py -3.12 backend\publish_feed.py --publish --local
pause
