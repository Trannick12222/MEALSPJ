@echo off
echo ====================================================
echo Railway Database Backup Tool (Python Only)
echo ====================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python not found. Please install Python first.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python found. Starting backup...
echo.

REM Run the simple backup script
python simple_backup.py

echo.
echo Press any key to exit...
pause >nul
