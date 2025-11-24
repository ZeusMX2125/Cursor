# CORS Fix Complete - Testing Guide

## Changes Applied

### 1. Clean CORS Setup ✅
- Removed all custom CORS middleware
- Using only `CORSMiddleware` from FastAPI
- Exception handlers return `JSONResponse` (CORSMiddleware adds headers automatically)

### 2. Exception Handlers ✅
- Added `RequestValidationError` handler
- `StarletteHTTPException` handler (covers `HTTPException`)
- Global `Exception` handler
- All return `JSONResponse` so CORS headers are added

### 3. Canary Routes Added ✅
- `GET /api/cors-ok` - Simple test endpoint
- `POST /api/cors-ok` - Simple test endpoint with payload

### 4. Improved Error Handling ✅
- Contracts endpoint: Better error messages, defensive mapping
- Flatten endpoint: Better error categorization (400 vs 500)
- All errors limited to 200 chars to prevent huge responses

## Testing Steps

### Step 1: Test Canary Routes (Prove CORS Works)

These should ALL show `Access-Control-Allow-Origin: http://localhost:3000`:

```bash
# Preflight (OPTIONS)
curl -i -X OPTIONS \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  http://localhost:8000/api/cors-ok

# Simple GET
curl -i -H "Origin: http://localhost:3000" \
  http://localhost:8000/api/cors-ok

# POST (no auth)
curl -i -X POST \
  -H "Origin: http://localhost:3000" \
  -H "Content-Type: application/json" \
  -d '{"hello": "world"}' \
  http://localhost:8000/api/cors-ok
```

**Expected:** All three should show `Access-Control-Allow-Origin: http://localhost:3000` in headers.

### Step 2: Test Real Endpoints Preflight

```bash
# GET contracts (no preflight needed, but test it)
curl -i -H "Origin: http://localhost:3000" \
  "http://localhost:8000/api/market/contracts?live=true"

# POST flatten preflight (if browser sends Authorization header)
curl -i -X OPTIONS \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: authorization,content-type" \
  http://localhost:8000/api/trading/accounts/14743844/flatten
```

**Expected:** Both should show `Access-Control-Allow-Origin: http://localhost:3000`.

### Step 3: Check Backend Logs

If CORS headers are present but you still get 500 errors, check:
- `backend/logs/backend_*.log` (most recent file)
- Terminal where backend is running

Look for:
- Authentication errors
- ProjectX API connection issues
- Missing environment variables

### Step 4: Test from Browser

1. Open browser DevTools (F12)
2. Go to Network tab
3. Load the trading page
4. Check the `/api/market/contracts` request:
   - Should show `Access-Control-Allow-Origin: http://localhost:3000` in Response Headers
   - Status should be 200, 4xx, or 5xx (not blocked by CORS)
5. Click "Flatten" button
6. Check the `/api/trading/accounts/{id}/flatten` request:
   - Should show CORS header
   - Should return JSON (even on error)

## What Success Looks Like

✅ **CORS Working:**
- Network tab shows `Access-Control-Allow-Origin: http://localhost:3000`
- No "CORS policy" errors in console
- Requests complete (even if they return 4xx/5xx)

✅ **500 Errors Fixed:**
- Backend logs show the actual error
- Frontend receives JSON error response: `{"detail": "..."}`
- Error messages are helpful (not just "Internal Server Error")

## Common Issues

### Issue: Still getting CORS errors
**Solution:** 
1. Restart backend after changes
2. Check canary routes first - if they don't show CORS header, middleware isn't working
3. Verify no custom middleware is interfering

### Issue: 500 errors but CORS header present
**Solution:**
- This is NOT a CORS issue anymore
- Check backend logs for the actual error
- Likely causes:
  - ProjectX service not initialized
  - Authentication failure
  - Missing environment variables
  - ProjectX API connection issue

### Issue: Canary routes work but real endpoints don't
**Solution:**
- The error is happening in the endpoint handler
- Check backend logs for the specific error
- The exception handler should catch it and return JSON with CORS

## Next Steps

1. **Restart backend** (required for changes to take effect)
2. **Test canary routes** first to prove CORS works
3. **Test real endpoints** and check logs for 500 causes
4. **Fix any ProjectX authentication/connection issues** if found

## Files Changed

- `backend/app.py`:
  - Added `RequestValidationError` handler
  - Added canary routes (`/api/cors-ok`)
  - Improved error handling in contracts and flatten endpoints
  - All exceptions now return `JSONResponse` (CORS middleware adds headers)


