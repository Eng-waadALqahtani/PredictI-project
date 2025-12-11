@echo off
echo ========================================
echo   PredictIQ - Feature Testing
echo ========================================
echo.

cd /d "%~dp0"
python backend\test_features.py

pause

