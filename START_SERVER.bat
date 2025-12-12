@echo off
echo ========================================
echo   Digital Threat Fingerprint - Server
echo ========================================
echo.

REM Check if venv exists in backend directory
if exist "backend\venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    cd backend
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
    cd backend
) else (
    echo Virtual environment not found!
    echo Please install dependencies first:
    echo   cd backend
    echo   python -m venv venv
    echo   venv\Scripts\python.exe -m pip install -r ..\requirements.txt
    pause
    exit /b 1
)

echo.
echo Starting Flask server...
echo Server will be available at: http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo.

python main.py

pause

