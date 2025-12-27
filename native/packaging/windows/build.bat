@echo off
REM WoW Stat Tracker - Windows Build Script
REM BSD 3-Clause License
REM
REM Builds the native Windows application.
REM
REM Usage: build.bat [Release|Debug]
REM

setlocal enabledelayedexpansion

set BUILD_TYPE=%1
if "%BUILD_TYPE%"=="" set BUILD_TYPE=Release

set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..\..

echo === WoW Stat Tracker Windows Build ===
echo Build type: %BUILD_TYPE%
echo Project dir: %PROJECT_DIR%

REM Create build directory
set BUILD_DIR=%PROJECT_DIR%\build-windows-%BUILD_TYPE%
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"
cd /d "%BUILD_DIR%"

REM Find Visual Studio
where cl >nul 2>&1
if errorlevel 1 (
    echo Error: Visual Studio not found in PATH.
    echo Please run this script from a Visual Studio Developer Command Prompt,
    echo or run vcvarsall.bat first.
    exit /b 1
)

REM Configure with CMake
echo.
echo === Configuring with CMake ===
cmake "%PROJECT_DIR%" ^
    -G "Visual Studio 17 2022" ^
    -A x64 ^
    -DCMAKE_BUILD_TYPE=%BUILD_TYPE% ^
    -DWST_BUILD_PLATFORM=ON ^
    -DWST_BUILD_GUI=ON ^
    -DWST_BUILD_TESTS=OFF ^
    -DWST_ENABLE_LTO=ON

if errorlevel 1 (
    echo CMake configuration failed.
    exit /b 1
)

REM Build
echo.
echo === Building ===
cmake --build . --config %BUILD_TYPE% --parallel

if errorlevel 1 (
    echo Build failed.
    exit /b 1
)

REM Check if executable was created
set EXE_PATH=%BUILD_DIR%\%BUILD_TYPE%\WoWStatTracker.exe
if not exist "%EXE_PATH%" (
    echo Error: Executable not found at %EXE_PATH%
    exit /b 1
)

echo.
echo === Build Complete ===
echo Executable: %EXE_PATH%
for %%F in ("%EXE_PATH%") do echo Size: %%~zF bytes

echo.
echo To create distribution package, run: packaging\windows\package.bat

endlocal
