@echo off
REM Install ML/AI dependencies for the trading bot
REM This script installs torch, stable-baselines3, gymnasium, and other ML packages

echo ========================================
echo Installing ML/AI Dependencies
echo ========================================
echo.

cd backend

echo Installing PyTorch (this may take a while)...
py -m pip install torch>=2.0.0 --index-url https://download.pytorch.org/whl/cpu --no-warn-script-location
if %errorlevel% neq 0 (
    echo Failed to install torch. Trying default index...
    py -m pip install torch>=2.0.0 --no-warn-script-location
)

echo.
echo Installing stable-baselines3...
py -m pip install stable-baselines3>=2.0.0 --no-warn-script-location

echo.
echo Installing gymnasium...
py -m pip install gymnasium>=0.29.0 --no-warn-script-location

echo.
echo Installing XGBoost (if not already installed)...
py -m pip install xgboost>=2.0.3 --no-warn-script-location

echo.
echo Installing scikit-learn (if not already installed)...
py -m pip install scikit-learn>=1.5.0 --no-warn-script-location

echo.
echo Installing joblib (for model serialization)...
py -m pip install joblib --no-warn-script-location

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Download TradingView Charting Library from:
echo    https://www.tradingview.com/charting-library/
echo 2. Extract charting_library folder to: frontend\public\charting_library\
echo 3. Run stop.bat then start.bat to restart services
echo.
pause

