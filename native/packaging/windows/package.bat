@echo off
REM WoW Stat Tracker - Windows Package Script
REM BSD 3-Clause License
REM
REM Creates a distributable ZIP file and optionally builds MSI installer.
REM
REM Usage: package.bat [--msi]
REM

setlocal enabledelayedexpansion

set BUILD_MSI=0
if "%1"=="--msi" set BUILD_MSI=1

set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..\..
set BUILD_DIR=%PROJECT_DIR%\build-windows-Release

REM Check for executable
set EXE_PATH=%BUILD_DIR%\Release\WoWStatTracker.exe
if not exist "%EXE_PATH%" (
    echo Error: Executable not found at %EXE_PATH%
    echo Run build.bat first.
    exit /b 1
)

REM Get version from CMake-generated VERSION file
set /p VERSION=<"%BUILD_DIR%\VERSION"
if "%VERSION%"=="" set VERSION=0.0.0

REM Create package directory
set PKG_NAME=WoWStatTracker-%VERSION%-windows-x64
set PKG_DIR=%BUILD_DIR%\%PKG_NAME%
if exist "%PKG_DIR%" rmdir /s /q "%PKG_DIR%"
mkdir "%PKG_DIR%"

echo === Creating Windows Package ===
echo Version: %VERSION%
echo Package: %PKG_NAME%

REM Copy executable
echo.
echo === Copying files ===
copy "%EXE_PATH%" "%PKG_DIR%\"

REM Copy addon if exists
set ADDON_SRC=%PROJECT_DIR%\..\WoWStatTracker_Addon
if exist "%ADDON_SRC%" (
    echo Copying addon...
    xcopy /E /I /Q "%ADDON_SRC%" "%PKG_DIR%\WoWStatTracker_Addon\"
)

REM Create README
echo Creating README...
(
echo WoW Stat Tracker %VERSION%
echo ========================
echo.
echo A native Windows application for tracking World of Warcraft character statistics.
echo.
echo INSTALLATION
echo ------------
echo 1. Extract this ZIP to any folder
echo 2. Run WoWStatTracker.exe
echo 3. Set your WoW installation path in File ^> Properties
echo 4. Copy the WoWStatTracker_Addon folder to your WoW addons directory:
echo    %%WOW_PATH%%\_retail_\Interface\AddOns\
echo.
echo USAGE
echo -----
echo 1. In WoW, log into each character and type: /wst update
echo 2. Type /reload to save the data
echo 3. In the app, click Addon ^> Import from Addon
echo.
echo LICENSE
echo -------
echo BSD 3-Clause License
echo.
echo For more information, visit:
echo https://github.com/yourusername/WoWStatTracker
) > "%PKG_DIR%\README.txt"

REM Create ZIP
echo.
echo === Creating ZIP archive ===
set ZIP_PATH=%BUILD_DIR%\%PKG_NAME%.zip
if exist "%ZIP_PATH%" del "%ZIP_PATH%"

REM Use PowerShell to create ZIP (available on Windows 10+)
powershell -NoProfile -Command "Compress-Archive -Path '%PKG_DIR%\*' -DestinationPath '%ZIP_PATH%' -Force"

if errorlevel 1 (
    echo Failed to create ZIP. Trying with tar...
    cd /d "%BUILD_DIR%"
    tar -a -cf "%PKG_NAME%.zip" "%PKG_NAME%"
)

echo.
echo ZIP created: %ZIP_PATH%
for %%F in ("%ZIP_PATH%") do echo Size: %%~zF bytes

REM Build MSI if requested
if %BUILD_MSI%==1 (
    echo.
    echo === Building MSI installer ===

    where candle >nul 2>&1
    if errorlevel 1 (
        echo Error: WiX Toolset not found in PATH.
        echo Install WiX Toolset from https://wixtoolset.org/
        echo or add it to PATH.
        goto :skip_msi
    )

    set WXS_PATH=%SCRIPT_DIR%WoWStatTracker.wxs
    set WIXOBJ_PATH=%BUILD_DIR%\WoWStatTracker.wixobj
    set MSI_PATH=%BUILD_DIR%\%PKG_NAME%.msi

    echo Compiling WiX source...
    candle -nologo -out "%WIXOBJ_PATH%" ^
        -dVersion=%VERSION% ^
        -dBuildDir=%BUILD_DIR%\Release ^
        -dAddonDir=%ADDON_SRC% ^
        "%WXS_PATH%"

    if errorlevel 1 (
        echo WiX compilation failed.
        goto :skip_msi
    )

    echo Linking MSI...
    light -nologo -out "%MSI_PATH%" ^
        -ext WixUIExtension ^
        "%WIXOBJ_PATH%"

    if errorlevel 1 (
        echo MSI linking failed.
        goto :skip_msi
    )

    echo.
    echo MSI created: %MSI_PATH%
    for %%F in ("%MSI_PATH%") do echo Size: %%~zF bytes
)

:skip_msi
echo.
echo === Package Complete ===
echo ZIP: %ZIP_PATH%
if %BUILD_MSI%==1 if exist "%MSI_PATH%" echo MSI: %MSI_PATH%

REM Cleanup
rmdir /s /q "%PKG_DIR%"

endlocal
