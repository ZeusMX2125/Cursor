@echo off
REM Start TopstepX Trading Bot - Backend and Frontend
REM This script starts both services with the latest code

echo ========================================
echo Starting TopstepX Trading Bot
echo ========================================
echo.

REM Check for Docker containers that might conflict
echo Checking for Docker containers on ports 8000 and 3000...
docker ps --format "{{.Names}}\t{{.Ports}}" 2>nul | findstr ":8000\|:3000" >nul
if %errorlevel% equ 0 (
    echo.
    echo WARNING: Docker containers detected on ports 8000 or 3000!
    echo.
    echo The following containers are using these ports:
    docker ps --format "table {{.Names}}\t{{.Ports}}" 2>nul | findstr ":8000\|:3000"
    echo.
    echo These containers may conflict with the .bat file startup.
    echo Please run stop.bat first to stop Docker containers, or run:
    echo   docker compose down
    echo   docker stop topstepx-engine cursor-backend-1 cursor-frontend-1
    echo.
    echo Press any key to continue anyway, or Ctrl+C to cancel...
    pause >nul
    echo.
)

REM Check if backend .env exists
if not exist "backend\.env" (
    echo WARNING: backend\.env file not found!
    echo Please create backend\.env with your TopstepX credentials.
    echo See backend\ENV_SETUP.md for instructions.
    echo.
)

REM Start Backend in new window
echo Starting Backend (http://localhost:8000)...
echo Using: py -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
REM Try py launcher first (more reliable on Windows), fallback to python
start "TopstepX Backend" cmd /k "cd /d %~dp0backend && py -m uvicorn app:app --reload --host 0.0.0.0 --port 8000 || python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000"

REM Wait a moment for backend to start
timeout /t 3 /nobreak >nul

REM Start Frontend in new window
echo Starting Frontend (http://localhost:3000)...
start "TopstepX Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ========================================
echo Services Starting...
echo ========================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Services are starting in separate windows.
echo.
echo To stop all services, run: stop.bat
echo Or close the command windows manually.
echo.
echo Waiting for services to initialize...
timeout /t 5 /nobreak >nul

echo.
echo Checking service status...
netstat -ano | findstr ":8000 :3000" >nul 2>&1
if %errorlevel% equ 0 (
    echo Services detected on ports 8000 and/or 3000
) else (
    echo No services detected yet. Check the windows for errors.
)

echo.
echo ========================================
echo IMPORTANT: If backend shows credential errors,
echo create backend\.env file with your TopstepX credentials.
echo See QUICK_FIX_ENV.md for instructions.
echo ========================================
echo.

pause

