# Troubleshooting Connection Refused Error

## Error: "localhost rechazó la conexión" (Connection Refused)

This error means the frontend server isn't running. Here's how to fix it:

## Quick Fix

### Option 1: Use the Start Script (Easiest)

**Windows:**
```cmd
start.bat
```

This will open two command windows - one for backend, one for frontend.

### Option 2: Manual Start

**Terminal 1 - Backend:**
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app:app --reload
```

Wait until you see: `Uvicorn running on http://0.0.0.0:8000`

**Terminal 2 - Frontend:**
```powershell
cd frontend
npm install
npm run dev
```

Wait until you see: `- Local: http://localhost:3000`

### Option 3: Check if Services Are Running

Check if ports are in use:
```powershell
netstat -ano | findstr ":8000"  # Backend
netstat -ano | findstr ":3000"  # Frontend
```

If nothing shows, the services aren't running.

## Common Issues

### 1. Python Not Found
**Solution:** Install Python 3.12+ from https://www.python.org/
- Check "Add Python to PATH" during installation
- Restart terminal after installation

### 2. npm Not Found
**Solution:** Install Node.js from https://nodejs.org/
- Download LTS version
- Restart terminal after installation

### 3. Port Already in Use
**Solution:** Kill the process or use different ports

**Kill process on port 3000:**
```powershell
netstat -ano | findstr ":3000"
# Note the PID from output, then:
taskkill /PID <PID> /F
```

**Or change port in frontend:**
Edit `frontend/package.json`:
```json
"dev": "next dev -p 3001"
```

### 4. Virtual Environment Issues
**Solution:** Recreate virtual environment
```powershell
cd backend
Remove-Item -Recurse -Force venv
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 5. Node Modules Missing
**Solution:** Reinstall dependencies
```powershell
cd frontend
Remove-Item -Recurse -Force node_modules
npm install
```

## Verification Steps

1. **Backend running?** Visit: http://localhost:8000/docs
   - Should show FastAPI documentation
   - If error, backend isn't running

2. **Frontend running?** Visit: http://localhost:3000
   - Should show the dashboard
   - If connection refused, frontend isn't running

3. **Both running?** Visit: http://localhost:3000/trading
   - Should show the trading interface

## Still Not Working?

1. Check Windows Firewall isn't blocking ports
2. Try running terminals as Administrator
3. Check antivirus isn't blocking Node.js/Python
4. Verify Python and Node.js are in PATH:
   ```powershell
   python --version
   node --version
   npm --version
   ```

## Alternative: Use Docker

If manual setup fails, use Docker:
```bash
docker-compose up
```

This starts everything automatically.


