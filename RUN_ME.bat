@echo off
setlocal
cd /d "%~dp0"
echo ============================================
echo YottaFlex Employee Lifecycle Challenge
echo ============================================
python --version
if errorlevel 1 (
  echo Python was not found. Install Python 3.10+ and enable Add Python to PATH.
  pause
  exit /b 1
)
echo Installing dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo Generating datasets and SQLite database...
python generate.py
if errorlevel 1 goto failed
echo Running validation...
python validate.py
if errorlevel 1 goto failed
echo Running automated tests...
python -m pytest -q
if errorlevel 1 goto failed
echo.
echo SUCCESS. Review data\, database\ and reports\.
pause
exit /b 0
:failed
echo.
echo Something failed. Read the error above and check README.md.
pause
exit /b 1
