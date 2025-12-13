@echo off
chcp 65001 >nul
echo ========================================
echo   PredictAI - عرض قاعدة البيانات
echo ========================================
echo.

cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
.venv\Scripts\python.exe backend\view_database.py %*

pause

