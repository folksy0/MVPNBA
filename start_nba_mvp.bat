@echo off
echo ========================================
echo NBA MVP Decision Support System
echo ========================================
echo.
echo Starting Flask application...
echo.

cd /d "C:\Users\Muhammad Zein\Downloads\template\dist"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python and try again.
    pause
    exit /b 1
)

REM Start the Flask application
echo Starting NBA MVP system...
echo Open your browser to: http://127.0.0.1:5000
echo Press Ctrl+C to stop the server
echo.

python app.py

pause
