@echo off
REM Windows batch launcher for the standalone gallery

echo 🚀 Launching SpritePal Detached Gallery...
echo ================================================

REM Navigate to script directory
cd /d "%~dp0"

REM Check if venv exists
if exist "..\venv\Scripts\python.exe" (
    echo 📦 Using virtual environment...
    "..\venv\Scripts\python.exe" launch_detached_gallery.py
) else (
    echo ❌ Virtual environment not found
    echo Please run: cd .. && python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt
    pause
    exit /b 1
)

echo 👋 Gallery closed
pause