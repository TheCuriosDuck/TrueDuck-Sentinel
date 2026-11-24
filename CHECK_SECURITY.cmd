@echo off
REM Run the simple static security checklist, then Python tests.
REM This does not certify the program safe for public use.
cd /d "%~dp0"
py -3.12 security_check.py
if errorlevel 1 (
  echo Review the FAIL messages above before publishing.
  pause
  exit /b 1
)
py -3.12 -m unittest discover -s tests -p "test_*.py"
if errorlevel 1 (
  echo One or more tests failed. Review the errors above.
  pause
  exit /b 1
)
REM Run JavaScript checks when Node.js is installed; don't require Node for end users.
where node >nul 2>nul
if not errorlevel 1 (
  node tests\detector.test.js || exit /b 1
  node tests\feed.test.js || exit /b 1
  node tests\lookup.test.js || exit /b 1
) else (
  echo Node.js not found: JavaScript tests skipped on this machine.
)
echo The preflight and tests passed. Browser and security review are STILL required.
pause
