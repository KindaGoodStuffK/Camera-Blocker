@echo off
:: Build and install updated HP CamBlock with all fixes
:: Right-click this file and select "Run as administrator"

echo ==========================================
echo   HP CamBlock - Build and Update
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

echo Step 1: Building updated executable...
echo.

cd /d "%~dp0"

:: Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

:: Build the executable
python build_app.py

:: Check if build succeeded
if not exist "dist\HP CamBlock.exe" (
    echo.
    echo ERROR: Build failed - HP CamBlock.exe not found!
    echo.
    pause
    exit /b 1
)

echo.
echo Step 2: Installing to Program Files...
echo.

:: Cleanup old versions
echo Removing old desktop shortcuts...
del /f /q "%USERPROFILE%\Desktop\HP CamBlock*.lnk" 2>nul
del /f /q "%USERPROFILE%\Desktop\Camera*.lnk" 2>nul
del /f /q "%USERPROFILE%\OneDrive\Desktop\HP CamBlock*.lnk" 2>nul
del /f /q "%USERPROFILE%\OneDrive\Desktop\Camera*.lnk" 2>nul

:: Remove old Start Menu entries
echo Removing old Start Menu entries...
rmdir /s /q "%ProgramData%\Microsoft\Windows\Start Menu\Programs\HP CamBlock" 2>nul

:: Remove old Program Files installation
echo Removing old Program Files installation...
if exist "%ProgramFiles%\HP CamBlock" (
    rmdir /s /q "%ProgramFiles%\HP CamBlock" 2>nul
    timeout /t 1 /nobreak >nul
)

:: Now create fresh directories
set "INSTALL_DIR=%ProgramFiles%\HP CamBlock"
set "START_MENU=%ProgramData%\Microsoft\Windows\Start Menu\Programs\HP CamBlock"

:: Create directories
echo Creating directories...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if not exist "%START_MENU%" mkdir "%START_MENU%"

:: Copy new executable
echo Copying updated executable...
copy /y "dist\HP CamBlock.exe" "%INSTALL_DIR%\" >nul

:: Create Start Menu shortcut
echo Creating Start Menu shortcut...
powershell -NoProfile -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%START_MENU%\HP CamBlock.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\HP CamBlock.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Save()" >nul 2>&1

:: Create Desktop shortcut
echo Creating Desktop shortcut...
powershell -NoProfile -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\HP CamBlock.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\HP CamBlock.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Save()" >nul 2>&1

:: Delete old desktop shortcuts (in case there were duplicates)
del /f /q "%USERPROFILE%\Desktop\HP CamBlock*.lnk" 2>nul
:: Recreate the correct one
powershell -NoProfile -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\HP CamBlock.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\HP CamBlock.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Save()" >nul 2>&1

echo.
echo ==========================================
echo   UPDATE COMPLETE!
echo ==========================================
echo.
echo Updated files:
echo   - %INSTALL_DIR%\HP CamBlock.exe
echo.
echo Shortcuts:
echo   - Start Menu ^> HP CamBlock
echo   - Desktop ^> HP CamBlock
echo.
echo The app now includes:
echo   - Fixed service restart with verification
echo   - PowerShell syntax fixes
echo   - Better error handling
echo   - Improved camera recovery
echo.
pause
