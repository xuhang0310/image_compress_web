@echo off
setlocal
title UV Project Manager
cd /d "%~dp0"

:: 1. Try to find uv in the system Path
set UV_BIN=uv
uv --version >nul 2>&1

:: 2. If not in Path, check the default Windows install location
if %errorlevel% neq 0 (
    set UV_BIN=%USERPROFILE%\.local\bin\uv.exe
    if not exist "!UV_BIN!" (
        echo [ERROR] uv.exe not found in Path or %USERPROFILE%\.local\bin\
        echo [FIX] Please run the install command in PowerShell first.
        pause
        exit /b
    )
)

:: 3. Sync environment using the found uv binary
echo [INFO] Syncing environment...
"%UV_BIN%" sync --link-mode copy --extra cpu

:: 4. Run application in background
echo [INFO] Starting...
echo ---------------------------------------
start /B cmd /c ""%UV_BIN%" run python main.py > app.log 2>&1"
echo [INFO] Application running in background
echo [INFO] Logs: app.log

timeout /t 2