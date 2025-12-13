@echo off
echo ========================================
echo   PredictAI - Feature Testing
echo ========================================
echo.

cd /d "%~dp0"
python backend\test_features.py

pause

