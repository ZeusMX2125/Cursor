# CORS Configuration Guide

## Current CORS Setup

CORS is handled by FastAPI's `CORSMiddleware` with:
- Default origins: `http://localhost:3000` and `http://127.0.0.1:3000`
- Optional additional origins via `CORS_ALLOW_ORIGINS` environment variable
- CORS headers automatically added to all responses (including errors)

## How CORS Works in This Backend
- The backend must be restarted after any CORS change.
- The browser origin (e.g. `http://127.0.0.1:3000`) must appear in the backend’s allowed-origins list.
- Error responses **must** include `Access-Control-Allow-Origin`; otherwise the browser treats them as CORS failures.

## Solution Steps

### Step 1: Stop the Backend Server
1. Find the terminal/command prompt where the backend is running
2. Press `Ctrl+C` to stop it
3. Wait for it to fully stop

### Step 2: Restart the Backend (always required after CORS changes)
```bash
cd backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Or if you're using a different command:
```bash
cd backend
python -m uvicorn app:app --reload
```

### Step 3: Run the automated CORS check
```
cd backend
python check_backend.py
```
The script calls `/`, `/api/test/cors`, `/api/market/contracts`, and `/health` with a localhost Origin header.  
✅ **Pass** = every response (including errors) shows `Access-Control-Allow-Origin`.  
❌ **Fail** = follow the script’s guidance (usually restart backend or add the origin).

### Step 4: Add extra origins when needed
If the frontend runs from a different URL (e.g. `https://studio.localhost`), set:
```
# backend/.env
CORS_ALLOW_ORIGINS=https://studio.localhost,http://localhost:3000
```
Restart the backend and rerun `python check_backend.py`.

## What the backend now enforces

1. **FastAPI CORSMiddleware** with sensible defaults (`http://localhost:3000`, `http://127.0.0.1:3000`) plus optional `CORS_ALLOW_ORIGINS` overrides.
2. **Global response wrapper** that re-attaches `Access-Control-Allow-Origin` on every response, even when an exception occurs.
3. **Unified exception handlers** so JSON errors are always returned (and now always have CORS headers).
4. **`backend/check_backend.py`** so you can prove headers are present before opening the browser.

## If Still Not Working

### Check Backend Logs
Look for errors in the backend terminal. Common issues:
- Authentication failure (check `.env` file)
- ProjectX API connection issues
- Port 8000 already in use

### Verify Backend is Actually Running
```bash
curl -i -H "Origin: http://localhost:3000" http://localhost:8000/api/cors-ok
```
You should see `Access-Control-Allow-Origin: http://localhost:3000` in the headers even if the response is an error.

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
✅ `/api/market/contracts` returns JSON (200/4xx/5xx) instead of “network error”  
✅ Flatten button returns structured JSON (success or error)  
✅ WebSocket connects (green indicator) once REST heartbeat succeeds

## Still Having Issues?

1. Check backend terminal for Python errors
2. Verify Python version (should be 3.8+)
3. Check if all dependencies are installed: `pip install -r requirements.txt`
4. Look for import errors in backend startup logs


