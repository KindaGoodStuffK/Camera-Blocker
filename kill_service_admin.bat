@echo off
:: Kill stuck Windows Camera Frame Server service
:: Right-click this file and select "Run as administrator"

echo ==========================================
echo   Kill Stuck Camera Service
echo ==========================================
echo.

:: Check if running as admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script must be run as Administrator!
    echo.
    echo Right-click on this file and select "Run as administrator"
    echo.
    pause
    exit /b 1
)

echo Killing stuck service and restarting...
echo.

:: Run the Python script
cd /d "%~dp0"
python kill_and_restart_service.py

echo.
echo ==========================================
echo   PROCESS COMPLETE
echo ==========================================
echo.
echo If service still won't start, restart your PC.
echo.
pause
