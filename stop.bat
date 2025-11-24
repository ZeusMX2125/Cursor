@echo off
echo === Stopping TopStepX Trading Bot ===
echo.

REM Kill processes by port - Backend (8000)
echo [1/5] Stopping backend on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo   Killing PID %%a
    taskkill /F /PID %%a >nul 2>&1
)

REM Kill processes by port - Frontend (3000)
echo [2/5] Stopping frontend on port 3000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000" ^| findstr "LISTENING"') do (
    echo   Killing PID %%a
    taskkill /F /PID %%a >nul 2>&1
)

REM Kill all Node.js processes (catches npm, next, etc.)
echo [3/5] Stopping all Node.js processes...
taskkill /F /IM node.exe >nul 2>&1
if %errorlevel% equ 0 (
    echo   ✓ Node.js processes stopped
) else (
    echo   (No Node.js processes found)
)

REM Kill Python processes running uvicorn (using PowerShell for better detection)
echo [4/5] Stopping Python/uvicorn processes...
powershell -Command "$procs = Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -like '*uvicorn*' }; if ($procs) { $procs | ForEach-Object { Stop-Process -Id $_.ProcessId -Force } }" >nul 2>&1
if %errorlevel% equ 0 (
    echo   ✓ Python/uvicorn processes stopped
) else (
    echo   (No uvicorn processes found)
)

REM Kill command windows with specific titles
echo [5/5] Closing command windows...
taskkill /F /FI "WINDOWTITLE eq Backend*" /IM cmd.exe >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Frontend*" /IM cmd.exe >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Backend Server*" /IM cmd.exe >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Frontend Server*" /IM cmd.exe >nul 2>&1

REM Wait for processes to terminate
timeout /t 2 /nobreak >nul

REM Final aggressive cleanup - kill anything still on ports
echo.
echo Final cleanup...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8000"') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":3000"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo ✓ All processes stopped
echo.
echo If you still see processes running:
echo   - Check Task Manager manually
echo   - Close any remaining command windows
echo.
pause
