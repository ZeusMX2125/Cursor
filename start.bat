@echo off
echo Starting TopstepX Trading Bot...
echo.

echo Starting Backend...
start "Backend" cmd /k "cd backend && python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt && uvicorn app:app --reload"

timeout /t 5 /nobreak >nul

echo Starting Frontend...
start "Frontend" cmd /k "cd frontend && npm install && npm run dev"

echo.
echo Services starting...
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo Trading Interface: http://localhost:3000/trading
echo.
pause


