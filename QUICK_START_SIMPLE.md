# Quick Start - Simple Commands

## 🚀 Start Both Servers

### Option 1: Use the Scripts (Easiest)

Open **TWO separate PowerShell windows**:

**Window 1 - Backend:**
```powershell
powershell -ExecutionPolicy Bypass -File .\START_BACKEND.ps1
```

**Window 2 - Frontend:**
```powershell
powershell -ExecutionPolicy Bypass -File .\START_FRONTEND.ps1
```

### Option 2: Manual Commands

**Window 1 - Backend:**
```powershell
cd backend
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app:app --reload
```

**Window 2 - Frontend:**
```powershell
cd frontend
npm install
npm run dev
```

## 🌐 Access the Interface

Wait 10-15 seconds, then open:

**http://localhost:3000/trading**

---

## ✅ Verify Node.js is Working

If you get "node not found" errors, run this first:
```powershell
powershell -ExecutionPolicy Bypass -File .\refresh_path.ps1
```

Or restart your PowerShell window (Node.js should be in PATH after installation).

---

## 📝 Notes

- Keep both PowerShell windows open while servers are running
- Backend runs on port 8000
- Frontend runs on port 3000
- The new ALGOX interface is at `/trading` route

