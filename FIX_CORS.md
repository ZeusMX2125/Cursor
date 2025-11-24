# CORS Error Fix Guide

## Problem
You're seeing: `Access to XMLHttpRequest at 'http://localhost:8000/api/market/contracts?live=true' from origin 'http://localhost:3000' has been blocked by CORS policy`

## Root Cause
The backend server needs to be **restarted** to apply the CORS middleware changes. The code is correct, but the running server doesn't have the new middleware.

## Solution Steps

### Step 1: Stop the Backend Server
1. Find the terminal/command prompt where the backend is running
2. Press `Ctrl+C` to stop it
3. Wait for it to fully stop

### Step 2: Restart the Backend
```bash
cd backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Or if you're using a different command:
```bash
cd backend
python -m uvicorn app:app --reload
```

### Step 3: Verify Backend is Running
Open in browser: http://localhost:8000/api/test/cors

You should see:
```json
{
  "message": "CORS test successful",
  "timestamp": "...",
  "cors_configured": true
}
```

### Step 4: Check Browser Console
1. Open http://localhost:3000/trading
2. Open DevTools (F12)
3. Check Network tab
4. Look for `/api/market/contracts` request
5. Check Response Headers - should include:
   - `Access-Control-Allow-Origin: http://localhost:3000`
   - `Access-Control-Allow-Credentials: true`

## What Was Fixed

1. **Added `EnsureCORSHeadersMiddleware`** - Guarantees CORS headers on ALL responses
2. **Separated HTTPException handler** - Ensures error responses have CORS headers
3. **Improved contracts endpoint** - Returns JSONResponse with CORS headers even on errors
4. **Better error logging** - Frontend now shows detailed error messages

## If Still Not Working

### Check Backend Logs
Look for errors in the backend terminal. Common issues:
- Authentication failure (check `.env` file)
- ProjectX API connection issues
- Port 8000 already in use

### Verify Backend is Actually Running
```bash
# Test if backend responds
curl http://localhost:8000/api/test/cors
```

### Check Firewall
Windows Firewall might be blocking port 8000. Temporarily disable to test.

### Verify .env File
Make sure `backend/.env` exists and has:
```
TOPSTEPX_USERNAME=your_username
TOPSTEPX_API_KEY=your_api_key
TOPSTEPX_BASE_URL=https://api.topstepx.com/api
```

## Expected Behavior After Fix

✅ No CORS errors in browser console
✅ Contracts dropdown loads in trading page
✅ All API calls work from frontend
✅ WebSocket connects successfully (green indicator)

## Still Having Issues?

1. Check backend terminal for Python errors
2. Verify Python version (should be 3.8+)
3. Check if all dependencies are installed: `pip install -r requirements.txt`
4. Look for import errors in backend startup logs


