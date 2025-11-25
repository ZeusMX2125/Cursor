# Quick Start Guide

## Starting the Bot

### Option 1: PowerShell Script (Recommended)
```powershell
.\start.ps1
```

### Option 2: Manual Start

**Terminal 1 - Backend:**
```bash
cd backend
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

## Stopping the Bot

### Option 1: PowerShell Script (Recommended)
```powershell
.\stop.ps1
```

### Option 2: Manual Stop
- Press `Ctrl+C` in each terminal
- Or kill processes on ports 8000 and 3000

## First Time Setup

### 1. Create Backend Environment File

Create `backend/.env` with your TopstepX credentials:

```ini
TOPSTEPX_USERNAME=your_username_here
TOPSTEPX_API_KEY=your_api_key_here
TOPSTEPX_BASE_URL=https://api.topstepx.com/api
TOPSTEPX_AUTH_MODE=login_key
TOPSTEPX_VALIDATE_TOKENS=true
```

**Get your API key from:** https://app.topstepx.com (Settings → API Access)

See `backend/ENV_SETUP.md` for detailed instructions.

### 2. Install Dependencies

**Backend:**
```bash
cd backend
pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend
npm install
```

## Accessing the Application

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **Backend Docs:** http://localhost:8000/docs

## Troubleshooting

### Backend won't start
- Check `backend/.env` exists with correct credentials
- See `backend/ENV_SETUP.md` for setup help
- Check backend terminal for error messages

### Frontend won't start
- Run `npm install` in `frontend/` directory
- Check if port 3000 is already in use

### CORS errors
- Make sure backend is running on port 8000
- Restart backend after any changes
- See `FIX_CORS.md` for details

### WebSocket won't connect
- Backend must be running and healthy
- Check `/health` endpoint: http://localhost:8000/health
- WebSocket waits for health check to pass

## Scripts

- `start.ps1` - Start both backend and frontend
- `stop.ps1` - Stop all services

## Documentation

- `backend/ENV_SETUP.md` - Environment variable setup
- `FIX_CORS.md` - CORS configuration
- `BACKEND_REFACTOR.md` - Technical refactor details
- `RESTART_INSTRUCTIONS.md` - How to restart after changes

