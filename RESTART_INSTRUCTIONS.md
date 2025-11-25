# How to Restart After Refactor

## Critical: Backend Must Be Restarted

The refactor created new files that must be loaded. Follow these steps exactly:

### 1. Stop Current Backend

Find the terminal where the backend is running and press `Ctrl+C` to stop it.

### 2. Verify Environment

Check that `backend/.env` exists with:
```ini
TOPSTEPX_USERNAME=your_username
TOPSTEPX_API_KEY=your_api_key
TOPSTEPX_BASE_URL=https://api.topstepx.com/api
```

If missing, see `backend/ENV_SETUP.md` for setup instructions.

### 3. Restart Backend

```bash
cd backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### 4. Watch for Success Messages

You should see:
```
CORS allowed origins: ['http://127.0.0.1:3000', 'http://localhost:3000']
V2 client initialized (Result-based error handling)
Authentication manager initialized successfully
```

### 5. Test Backend

```bash
cd backend
python check_backend.py
```

All tests should show `[OK]` and CORS headers.

### 6. Reload Frontend

Refresh the browser at http://localhost:3000/trading

Expected:
- ✅ No CORS errors
- ✅ Contracts load (or show clear error message)
- ✅ WebSocket connects (green indicator)

## If Backend Won't Start

### Error: "Failed to load settings"
- Check `.env` file exists in `backend/` directory
- Verify it has `TOPSTEPX_USERNAME` and `TOPSTEPX_API_KEY`
- See `backend/ENV_SETUP.md`

### Error: "Auth mode 'login_key' requires..."
- Missing credentials in `.env`
- Add `TOPSTEPX_USERNAME` and `TOPSTEPX_API_KEY`

### Error: Import errors
- Install dependencies:
  ```bash
  cd backend
  pip install -r requirements.txt
  ```

## Key Changes

1. **Result-based error handling** - API errors return JSON, not crash
2. **V2 client** - Runs alongside V1 for gradual migration
3. **Guaranteed CORS** - All responses include headers
4. **Better diagnostics** - Clear error messages

After restarting, the CORS and 500 errors should be resolved.

