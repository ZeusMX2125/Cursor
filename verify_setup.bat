@echo off
REM Verify setup after overhaul
REM Checks if all critical components are in place

echo ========================================
echo Verifying Overhaul Setup
echo ========================================
echo.

set ERRORS=0

REM Check TradingView Library
echo [1/5] Checking TradingView Library...
if exist "frontend\public\charting_library\charting_library.standalone.js" (
    for %%F in ("frontend\public\charting_library\charting_library.standalone.js") do (
        set SIZE=%%~zF
        if !SIZE! LSS 1000 (
            echo   WARNING: TradingView library file is too small (likely placeholder)
            echo   You need to download the actual library from TradingView website
            set /a ERRORS+=1
        ) else (
            echo   OK: TradingView library found (!SIZE! bytes)
        )
    )
) else (
    echo   ERROR: TradingView library not found!
    echo   Expected: frontend\public\charting_library\charting_library.standalone.js
    set /a ERRORS+=1
)

REM Check ML model directories
echo.
echo [2/5] Checking ML model directories...
if exist "backend\ml\models" (
    echo   OK: Models directory exists
) else (
    echo   WARNING: Models directory missing (will be created automatically)
    mkdir backend\ml\models 2>nul
)

REM Check requirements.txt has ML dependencies
echo.
echo [3/5] Checking requirements.txt...
findstr /C:"torch" backend\requirements.txt >nul
if %errorlevel% equ 0 (
    echo   OK: torch found in requirements.txt
) else (
    echo   ERROR: torch not in requirements.txt
    set /a ERRORS+=1
)

findstr /C:"stable-baselines3" backend\requirements.txt >nul
if %errorlevel% equ 0 (
    echo   OK: stable-baselines3 found in requirements.txt
) else (
    echo   ERROR: stable-baselines3 not in requirements.txt
    set /a ERRORS+=1
)

REM Check ML endpoints file
echo.
echo [4/5] Checking ML endpoints...
if exist "backend\api\ml_endpoints.py" (
    echo   OK: ML endpoints file exists
) else (
    echo   ERROR: ML endpoints file missing!
    set /a ERRORS+=1
)

REM Check TradingView components
echo.
echo [5/5] Checking TradingView components...
if exist "frontend\lib\tradingview-datafeed.ts" (
    echo   OK: TradingView datafeed exists
) else (
    echo   ERROR: TradingView datafeed missing!
    set /a ERRORS+=1
)

if exist "frontend\components\TradingViewChart.tsx" (
    echo   OK: TradingViewChart component exists
) else (
    echo   ERROR: TradingViewChart component missing!
    set /a ERRORS+=1
)

echo.
echo ========================================
if %ERRORS% equ 0 (
    echo Setup Verification: PASSED
    echo.
    echo All critical components are in place!
    echo.
    echo Next: Run install_ml_dependencies.bat to install Python packages
    echo Then: Download TradingView library (see TRADINGVIEW_INSTALL.md)
    echo Finally: Run stop.bat then start.bat
) else (
    echo Setup Verification: FAILED (%ERRORS% errors)
    echo.
    echo Please fix the errors above before proceeding.
)
echo ========================================
echo.
pause

