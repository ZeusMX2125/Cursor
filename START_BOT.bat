@echo off
echo === Starting TopStepX Trading Bot ===
echo.

REM Check if credentials are set
if not exist "backend\.env" (
    echo ERROR: backend/.env file not found!
    echo Run: setup_credentials.ps1
    pause
    exit /b 1
)

REM Start backend in new window
echo Starting backend server...
start "Backend Server" cmd /k "cd /d %~dp0backend && py -m uvicorn app:app --reload --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

REM Start frontend in new window
echo Starting frontend server...
start "Frontend Server" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ✓ Servers starting...
echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo.
timeout /t 2 /nobreak >nul
start http://localhost:3000

pause

