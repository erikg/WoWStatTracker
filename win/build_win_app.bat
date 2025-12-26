@echo off
REM Build script for WoW Stat Tracker Windows App
REM This script creates a standalone Windows application
REM
REM PREREQUISITES:
REM   1. MSYS2 installed at C:\msys64
REM   2. Run in MSYS2 MINGW64 shell, or have MINGW64 bin in PATH
REM   3. GTK3 and PyGObject installed via pacman
REM   4. PyInstaller installed (pip install pyinstaller)
REM
REM See SETUP.md for detailed installation instructions.

setlocal enabledelayedexpansion

echo Building WoW Stat Tracker Windows App...

REM Change to project root directory
cd /d "%~dp0\.."

REM Check for MSYS2 and set up environment
if exist "C:\msys64\mingw64\bin" (
    set "PATH=C:\msys64\mingw64\bin;%PATH%"
    set "MINGW_PREFIX=C:\msys64\mingw64"
    echo Found MSYS2 MINGW64 at C:\msys64
) else if exist "C:\msys64\ucrt64\bin" (
    set "PATH=C:\msys64\ucrt64\bin;%PATH%"
    set "MINGW_PREFIX=C:\msys64\ucrt64"
    echo Found MSYS2 UCRT64 at C:\msys64
) else (
    echo ERROR: MSYS2 not found at C:\msys64
    echo Please install MSYS2 from https://www.msys2.org/
    exit /b 1
)

REM Check if PyInstaller is available
where pyinstaller >nul 2>nul
if errorlevel 1 (
    echo ERROR: PyInstaller not found. Please install it with: pip install pyinstaller
    exit /b 1
)

REM Check for GTK installation
python -c "import gi" 2>nul
if errorlevel 1 (
    echo ERROR: PyGObject not found.
    echo Please install in MSYS2 MINGW64 shell:
    echo   pacman -S mingw-w64-x86_64-gtk3 mingw-w64-x86_64-python-gobject
    exit /b 1
)

echo GTK libraries found

REM Set HOME and USERPROFILE for PyInstaller (fixes "Could not determine home directory" error)
set "HOME=%USERPROFILE%"

REM Clean previous builds
echo Cleaning previous builds...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

REM Build the app
echo Building Windows application...
pyinstaller win\WoWStatTracker.spec --clean --noconfirm

REM Check if build was successful
if exist "dist\WoWStatTracker\WoWStatTracker.exe" (
    echo.
    echo Build successful!
    echo Windows app created at: dist\WoWStatTracker\
    echo.
    echo To run the app:
    echo   dist\WoWStatTracker\WoWStatTracker.exe
    echo.
    echo To create a distributable ZIP:
    echo   powershell Compress-Archive -Path dist\WoWStatTracker -DestinationPath dist\WoWStatTracker-Windows.zip
    echo.
) else (
    echo.
    echo ERROR: Build failed. Check the output above for errors.
    exit /b 1
)

endlocal
