@echo off
:: Build and install HP CamBlock in one step

echo ==========================================
echo   HP CamBlock - Build and Install
echo ==========================================
echo.

:: Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

echo Step 1: Building executable...
echo.
python build_app.py

:: Check if build succeeded by looking for the exe
if not exist "dist\HP CamBlock.exe" (
    echo.
    echo ERROR: Build failed - HP CamBlock.exe not found in dist folder!
    echo Check the error messages above.
    echo.
    pause
    exit /b 1
)

echo.
echo Step 2: Installing...
echo.
call install_simple.bat
