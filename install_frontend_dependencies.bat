@echo off
REM Install frontend dependencies including Lightweight Charts
REM This script installs npm packages for the frontend

echo ========================================
echo Installing Frontend Dependencies
echo ========================================
echo.

cd frontend

echo Installing lightweight-charts and other dependencies...
call npm install

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo Frontend dependencies installed successfully!
    echo ========================================
) else (
    echo.
    echo ========================================
    echo Installation failed. Check npm is installed.
    echo ========================================
)

echo.
pause

