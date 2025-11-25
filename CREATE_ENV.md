# Create .env File

## Your Credentials

I've prepared your credentials. Create the file manually:

**File:** `backend/.env`

**Contents:**
```ini
# TopstepX / ProjectX API Credentials
TOPSTEPX_USERNAME=zeus2026
TOPSTEPX_API_KEY=0WOCdekBbvzBmetUucgg1NU/4FyIMso4j+XkTYBbn2Q=

# TopstepX API Base URL (DO NOT CHANGE)
TOPSTEPX_BASE_URL=https://api.topstepx.com/api

# Authentication Mode
TOPSTEPX_AUTH_MODE=login_key

# Token Validation
TOPSTEPX_VALIDATE_TOKENS=true

# Trading Configuration
ACCOUNT_SIZE=50000
PROFIT_TARGET=3000
DAILY_LOSS_LIMIT=1000
MAX_DRAWDOWN_LIMIT=2000
PAPER_TRADING_MODE=true
LOG_LEVEL=INFO
```

## Quick Steps

1. **Open** `backend/.env` in a text editor (create it if it doesn't exist)
2. **Copy and paste** the contents above
3. **Save** the file
4. **Run** `start.bat` to restart services

## After Creating .env

Run:
```batch
start.bat
```

The backend should now start successfully with your credentials!

