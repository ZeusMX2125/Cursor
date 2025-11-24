#!/bin/bash

echo "Starting TopstepX Trading Bot..."
echo ""

# Start backend
echo "Starting Backend..."
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload &
BACKEND_PID=$!
cd ..

# Wait a bit for backend to start
sleep 5

# Start frontend
echo "Starting Frontend..."
cd frontend
npm install
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "Services starting..."
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "Trading Interface: http://localhost:3000/trading"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for user interrupt
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait

