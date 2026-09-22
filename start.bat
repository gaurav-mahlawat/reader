@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Python not found. Install Python 3.11+ from https://www.python.org/
        pause
        exit /b 1
    )
)

echo Installing dependencies...
".venv\Scripts\pip.exe" install -r requirements.txt -q
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo Starting Reader at http://127.0.0.1:8000
echo Press Ctrl+C to stop the server.
echo.

".venv\Scripts\python.exe" run.py
pause
