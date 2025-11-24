# Quick Start Guide

## Fix PowerShell Execution Policy Issue

You have 3 options:

### Option 1: Use .bat files (Easiest - No admin needed)
Just double-click:
- `START_BOT.bat` - Starts both servers
- OR run separately:
  - `start_backend.bat` - Backend only
  - `start_frontend.bat` - Frontend only

### Option 2: Bypass policy for this session
```powershell
powershell -ExecutionPolicy Bypass -File .\START_BOT.ps1
```

### Option 3: Change execution policy (Requires Admin)
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Then you can run: `.\START_BOT.ps1`

## Before Starting

1. **Add your credentials** to `backend/.env`:
   ```
   TOPSTEPX_USERNAME=your_username
   TOPSTEPX_API_KEY=your_api_key
   ```

2. **Or run the setup script**:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\setup_credentials.ps1
   ```

## Start the Bot

**Easiest way:**
- Double-click `START_BOT.bat`

**Or manually:**
1. Open terminal 1: `start_backend.bat`
2. Open terminal 2: `start_frontend.bat`
3. Open browser: http://localhost:3000

## Stop the Bot

**Easiest way:**
- Double-click `STOP_BOT.bat`

**Or manually:**
- `stop_backend.bat` - Stop backend only
- `stop_frontend.bat` - Stop frontend only

**Or use PowerShell:**
```powershell
powershell -ExecutionPolicy Bypass -File .\STOP_BOT.ps1
```

## Access Points

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
