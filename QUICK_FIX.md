# Quick Fix for Connection Refused Error

## 🚨 The Problem
You're seeing "localhost rechazó la conexión" because the servers aren't running.

## ✅ Solution - Run This Script

**Right-click on `START_SERVERS.ps1` and select "Run with PowerShell"**

Or run in PowerShell:
```powershell
.\START_SERVERS.ps1
```

This will:
1. Check if Python and Node.js are installed
2. Start the backend server (port 8000)
3. Start the frontend server (port 3000)
4. Open two new windows (keep them open!)

## ⏱️ Wait 10-15 seconds

Then visit: **http://localhost:3000/trading**

## 🔍 Manual Check

If the script doesn't work, check:

1. **Python installed?**
   ```powershell
   python --version
   ```
   If error, install from: https://www.python.org/

2. **Node.js installed?**
   ```powershell
   node --version
   ```
   If error, install from: https://nodejs.org/

3. **Are servers running?**
   ```powershell
   netstat -ano | findstr ":8000"  # Should show backend
   netstat -ano | findstr ":3000"  # Should show frontend
   ```

## 📝 Manual Start (If Script Fails)

**Open TWO separate PowerShell windows:**

**Window 1 - Backend:**
```powershell
cd C:\Users\zeus2\OneDrive\Music\Escritorio\Cursor\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app:app --reload
```

**Window 2 - Frontend:**
```powershell
cd C:\Users\zeus2\OneDrive\Music\Escritorio\Cursor\frontend
npm install
npm run dev
```

**Keep both windows open!** Then visit http://localhost:3000/trading


