# Environment Setup Guide

## Required Environment Variables

Create a `backend/.env` file with the following variables:

```ini
# TopstepX / ProjectX API Credentials (REQUIRED)
# Get your API key from: https://app.topstepx.com (Settings → API Access)
TOPSTEPX_USERNAME=your_username_here
TOPSTEPX_API_KEY=your_api_key_here

# TopstepX API Base URL (DO NOT CHANGE)
TOPSTEPX_BASE_URL=https://api.topstepx.com/api

# Authentication Mode (use "login_key" for standard users)
TOPSTEPX_AUTH_MODE=login_key

# Token Validation (recommended: keep enabled)
TOPSTEPX_VALIDATE_TOKENS=true
```

## Optional Variables

```ini
# CORS - Additional allowed origins (comma-separated)
# CORS_ALLOW_ORIGINS=http://localhost:3001

# Trading Config
ACCOUNT_SIZE=50000
PROFIT_TARGET=3000
DAILY_LOSS_LIMIT=1000
MAX_DRAWDOWN_LIMIT=2000
PAPER_TRADING_MODE=true
LOG_LEVEL=INFO
```

## Authentication Endpoints

- **API Endpoint:** `https://api.topstepx.com`
- **User Hub (SignalR):** `https://rtc.topstepx.com/hubs/user`
- **Market Hub (SignalR):** `https://rtc.topstepx.com/hubs/market`

## References

- TopstepX API Access: https://help.topstep.com/en/articles/11187768-topstepx-api-access
- ProjectX Gateway API: https://gateway.docs.projectx.com/docs/intro/

## Common Issues

1. **Invalid credentials** → errorCode: 1 or 3
2. **Missing .env file** → Backend won't start
3. **Wrong base URL** → 404 errors on auth
4. **BOM in .env** → Use UTF-8 encoding, no BOM

