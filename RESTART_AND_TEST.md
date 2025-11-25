# Restart Backend and Test

## Critical: Backend Must Be Restarted

The backend needs to be restarted to pick up the latest code changes. The 500 errors you're seeing are likely because the backend is running old code.

## Steps to Fix

### 1. Stop All Services
```batch
stop.bat
```
Or manually close the backend and frontend command windows.

### 2. Start Services with Latest Code
```batch
start.bat
```

### 3. Verify Backend Started Correctly

Look in the backend terminal window for:
- ✅ "V2 client initialized (Result-based error handling)"
- ✅ "Authentication manager initialized successfully"
- ✅ "CORS allowed origins: ..."
- ❌ NO errors about missing credentials
- ❌ NO import errors

### 4. Test the Debug Endpoint

Open in browser or use curl:
```
http://localhost:8000/api/debug/contracts-test
```

This will show:
- If V2 service is initialized
- The actual error (if any)
- Sample contracts (if successful)

### 5. Test CORS Endpoint

```
http://localhost:8000/api/cors-ok
```

Should return: `{"ok": true}` with CORS headers.

### 6. Test Contracts Endpoint

```
http://localhost:8000/api/market/contracts?live=true
```

Should return a JSON array of contracts with CORS headers.

## What Was Fixed

1. **Better Error Handling**: Added try-catch blocks around the contracts endpoint
2. **Type Narrowing**: Fixed Result type handling to properly check for Error vs Success
3. **Debug Endpoint**: Added `/api/debug/contracts-test` to diagnose issues
4. **CORS**: Already configured with CORSMiddleware

## If Still Getting 500 Errors

1. Check backend terminal for the actual error message
2. Verify `.env` file exists in `backend/` directory
3. Verify credentials are correct:
   - `TOPSTEPX_USERNAME=zeus2026`
   - `TOPSTEPX_API_KEY=0WOCdekBbvzBmetUucgg1NU/4FyIMso4j+XkTYBbn2Q=`
4. Check backend logs for authentication errors
5. Test the debug endpoint to see the actual error

## Expected Behavior After Restart

- ✅ Backend starts without errors
- ✅ Health endpoint returns 200: `http://localhost:8000/health`
- ✅ CORS endpoint returns 200: `http://localhost:8000/api/cors-ok`
- ✅ Contracts endpoint returns 200 with contracts array
- ✅ Frontend can connect to backend
- ✅ WebSocket connects successfully

