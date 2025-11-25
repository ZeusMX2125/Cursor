@echo off
setlocal enabledelayedexpansion
REM Stop TopstepX Trading Bot - Backend and Frontend
REM This script stops all running bot services (Docker containers and direct processes)

echo ========================================
echo Stopping TopstepX Trading Bot
echo ========================================
echo.

REM Prevent script from exiting on errors
set "ERROR_OCCURRED=0"

REM Check for and stop Docker containers
echo Checking for Docker containers...
where docker >nul 2>&1
if !errorlevel! equ 0 (
    echo Stopping Docker containers...
    REM Stop known container names directly (simpler and more reliable)
    docker stop topstepx-engine topstepx-bridge topstepx-ui cursor-backend-1 cursor-frontend-1 2>nul
    if !errorlevel! neq 0 set "ERROR_OCCURRED=1"
    REM Also try docker compose down if docker-compose.yml exists
    if exist "docker-compose.yml" (
        docker compose down 2>nul
        if !errorlevel! neq 0 set "ERROR_OCCURRED=1"
    )
    echo Docker containers stopped.
) else (
    echo Docker not found in PATH (skipping Docker check).
)
echo.

REM Kill processes on port 8000 (Backend)
echo Checking for processes on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo Stopping process on port 8000 (PID: %%a)
    taskkill /F /PID %%a >nul 2>&1
)

REM Kill processes on port 3000 (Frontend)
echo Checking for processes on port 3000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000" ^| findstr "LISTENING"') do (
    echo Stopping process on port 3000 (PID: %%a)
    taskkill /F /PID %%a >nul 2>&1
)

REM Kill any Python processes running uvicorn (simplified)
echo Checking for uvicorn processes...
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST 2^>nul ^| findstr /I "PID"') do (
    echo Checking Python process %%a
    wmic process where "ProcessId=%%a" get CommandLine 2>nul | findstr /I "uvicorn" >nul
    if !errorlevel! equ 0 (
        echo Stopping uvicorn process (PID: %%a)
        taskkill /F /PID %%a >nul 2>&1
    )
)

REM Kill any Node processes running npm
echo Checking for npm/node processes...
tasklist /FI "IMAGENAME eq node.exe" /FO CSV 2>nul | findstr /I "node" >nul
if !errorlevel! equ 0 (
    for /f "tokens=2 delims=," %%a in ('tasklist /FI "IMAGENAME eq node.exe" /FO CSV 2^>nul ^| findstr /I "node"') do (
        if not "%%a"=="" (
            echo Stopping Node process (PID: %%a)
            taskkill /F /PID %%a >nul 2>&1
        )
    )
)

echo.
echo ========================================
echo All services stopped.
echo ========================================
echo.
echo Stopped:
echo   - Docker containers (if any)
echo   - Processes on port 8000 (Backend)
echo   - Processes on port 3000 (Frontend)
echo   - Python uvicorn processes
echo   - Node.js processes
echo.
echo You can now run start.bat to start services with the latest code.
echo.

pause

