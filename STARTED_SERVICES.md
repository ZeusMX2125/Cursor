# Services Started

## Status

I've started both backend and frontend in separate PowerShell windows.

## ⚠️ CRITICAL: Missing .env File

**Your backend will crash because `backend/.env` is missing!**

### Quick Fix:

1. **Open** `backend/.env` (create it if it doesn't exist)

2. **Add your credentials:**
```ini
TOPSTEPX_USERNAME=your_username_here
TOPSTEPX_API_KEY=your_api_key_here
TOPSTEPX_BASE_URL=https://api.topstepx.com/api
TOPSTEPX_AUTH_MODE=login_key
TOPSTEPX_VALIDATE_TOKENS=true
```

3. **Get your API key from:** https://app.topstepx.com (Settings → API Access)

4. **Restart backend** - Close the backend window and run `.\start.ps1` again

## What to Check

### Backend Window
- Look for errors about missing `.env` or credentials
- Should see: "CORS allowed origins: ..."
- Should see: "V2 client initialized"
- If you see credential errors → Create `backend/.env` file

### Frontend Window  
- Should see: "Ready on http://localhost:3000"
- If you see errors → Run `npm install` in `frontend/` directory

## Access

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **Backend Docs:** http://localhost:8000/docs

## Stop Services

Run: `.\stop.ps1`

Or manually close the PowerShell windows.

## Next Steps

1. **Create `backend/.env`** with your credentials (see above)
2. **Restart backend** after creating .env
3. **Test in browser:** http://localhost:3000/trading
4. **Check for CORS errors** - Should be gone after restart with .env

See `QUICK_FIX_ENV.md` for more details.

