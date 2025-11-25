# TopstepX Trading Bot

## Quick Start

### 1. Create Backend Environment File

**Create `backend/.env` with your credentials:**

```ini
TOPSTEPX_USERNAME=zeus2026
TOPSTEPX_API_KEY=0WOCdekBbvzBmetUucgg1NU/4FyIMso4j+XkTYBbn2Q=
TOPSTEPX_BASE_URL=https://api.topstepx.com/api
TOPSTEPX_AUTH_MODE=login_key
TOPSTEPX_VALIDATE_TOKENS=true
ACCOUNT_SIZE=50000
PROFIT_TARGET=3000
DAILY_LOSS_LIMIT=1000
MAX_DRAWDOWN_LIMIT=2000
PAPER_TRADING_MODE=true
LOG_LEVEL=INFO
```

### 2. Start Services

**Double-click `start.bat`** or run:
```batch
start.bat
```

This opens two windows:
- **Backend** on http://localhost:8000
- **Frontend** on http://localhost:3000

### 3. Stop Services

**Double-click `stop.bat`** or run:
```batch
stop.bat
```

## Access

- **Frontend:** http://localhost:3000/trading
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

## First Time Setup

### Backend Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Frontend Dependencies
```bash
cd frontend
npm install
```

## Troubleshooting

### Backend crashes
- Check `backend/.env` exists with correct credentials
- See `backend/ENV_SETUP.md` for details

### CORS errors
- Make sure backend is running
- Restart backend after any changes
- See `FIX_CORS.md` for details

### Port already in use
- Run `stop.bat` to kill all services
- Then run `start.bat` again

## Documentation

- `SETUP_COMPLETE.md` - Complete setup guide
- `CREATE_ENV.md` - .env file contents
- `backend/ENV_SETUP.md` - Environment variables
- `FIX_CORS.md` - CORS configuration
- `BACKEND_REFACTOR.md` - Technical details

## Scripts

- **`start.bat`** - Start backend and frontend
- **`stop.bat`** - Stop all services

That's it! Just two scripts to manage everything.
