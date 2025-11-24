# Install Node.js - Required for Frontend

## 🚨 Node.js is Not Installed

You need Node.js to run the frontend. Here's how to install it:

## 📥 Installation Steps

### Option 1: Official Installer (Recommended)

1. **Download Node.js:**
   - Go to: https://nodejs.org/
   - Download the **LTS version** (Long Term Support)
   - Choose the Windows Installer (.msi)

2. **Install:**
   - Run the installer
   - Click "Next" through the setup
   - **IMPORTANT:** Make sure "Add to PATH" is checked
   - Click "Install"

3. **Restart PowerShell:**
   - Close your current PowerShell window
   - Open a new PowerShell window

4. **Verify Installation:**
   ```powershell
   node --version
   npm --version
   ```
   You should see version numbers.

### Option 2: Using Winget (Windows Package Manager)

```powershell
winget install OpenJS.NodeJS.LTS
```

Then restart PowerShell.

### Option 3: Using Chocolatey

If you have Chocolatey installed:
```powershell
choco install nodejs-lts
```

## ✅ After Installation

Once Node.js is installed, you can start the servers:

```powershell
powershell -ExecutionPolicy Bypass -File .\START_SERVERS_FIXED.ps1
```

Or manually:

**Backend:**
```powershell
cd backend
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app:app --reload
```

**Frontend:**
```powershell
cd frontend
npm install
npm run dev
```

Then visit: **http://localhost:3000/trading**

---

## 🔍 Quick Check

Run this to see if Node.js is installed:
```powershell
node --version
```

If you get an error, Node.js is not installed or not in your PATH.

