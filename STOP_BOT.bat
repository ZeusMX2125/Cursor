@echo off
echo === Stopping TopStepX Trading Bot ===
echo.

REM Find and kill backend server (uvicorn on port 8000)
echo Stopping backend server...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    echo Killing process %%a (backend)
    taskkill /F /PID %%a >nul 2>&1
)

REM Find and kill frontend server (node on port 3000)
echo Stopping frontend server...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING') do (
    echo Killing process %%a (frontend)
    taskkill /F /PID %%a >nul 2>&1
)

REM Also try to kill by process name (backup method)
taskkill /F /IM node.exe /FI "WINDOWTITLE eq *npm*" >nul 2>&1
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *uvicorn*" >nul 2>&1
taskkill /F /IM py.exe /FI "WINDOWTITLE eq *uvicorn*" >nul 2>&1

echo.
echo ✓ Servers stopped
echo.
pause

