@echo off
chcp 65001 >nul
cd /d "%~dp0"
python "SCRIPT_NAME.py"
echo.
echo ============================================
echo Nhan phim bat ky de dong cua so...
pause >nul
