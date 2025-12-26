@echo off
REM Create distributable ZIP file for Windows
REM Similar to mac/create_dmg.sh

setlocal enabledelayedexpansion

REM Change to project root directory
cd /d "%~dp0\.."

set APP_NAME=WoWStatTracker
set ZIP_NAME=%APP_NAME%-1.0.0.zip
set APP_PATH=dist\%APP_NAME%

REM Check app exists
if not exist "%APP_PATH%\%APP_NAME%.exe" (
    echo Error: %APP_PATH%\%APP_NAME%.exe not found.
    echo Run win\build_win_app.bat first.
    exit /b 1
)

REM Clean up any previous ZIP
if exist "dist\%ZIP_NAME%" del "dist\%ZIP_NAME%"

echo Creating ZIP archive...

REM Create ZIP using PowerShell (compress contents, not the directory itself)
powershell -Command "Compress-Archive -Path '%APP_PATH%\*' -DestinationPath 'dist\%ZIP_NAME%' -Force"

if exist "dist\%ZIP_NAME%" (
    echo.
    echo Created dist\%ZIP_NAME%
    echo.
    powershell -Command "(Get-Item 'dist\%ZIP_NAME%').Length / 1MB" | set /p SIZE=
    for %%A in ("dist\%ZIP_NAME%") do echo Size: %%~zA bytes
    echo.
) else (
    echo.
    echo ERROR: Failed to create ZIP file.
    exit /b 1
)

endlocal
