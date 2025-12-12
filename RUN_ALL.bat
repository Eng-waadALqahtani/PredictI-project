@echo off
echo ========================================
echo   Digital Threat Fingerprint System
echo   تشغيل النظام الكامل
echo ========================================
echo.

REM Activate virtual environment
if exist ".venv\Scripts\activate.bat" (
    echo [1/3] تفعيل البيئة الافتراضية...
    call .venv\Scripts\activate.bat
) else (
    echo [ERROR] Virtual environment not found!
    echo Please run: python -m venv .venv
    pause
    exit /b 1
)

REM Check if model exists
if not exist "ml\models\isoforest_absher.pkl" (
    echo [WARNING] Model file not found!
    echo Please train the model first by running ml/notebooks/train_isoforest.ipynb
    echo.
    pause
)

REM Start Flask server
echo [2/3] بدء تشغيل السيرفر...
echo.
echo ========================================
echo   النظام جاهز!
echo ========================================
echo.
echo الصفحات المتاحة:
echo   - توكلنا:     http://localhost:5000/tawakkalna-login.html
echo   - أبشر:       http://localhost:5000/absher-login
echo   - Dashboard:  http://localhost:5000/dashboard.html
echo   - SOC Admin:  http://localhost:5000/soc-admin-dashboard.html
echo.
echo اضغط Ctrl+C لإيقاف السيرفر
echo ========================================
echo.

cd backend
python main.py

pause

