# Easiest Way to Get Started

## 🎯 Recommended: Install Docker Desktop

Since you already have the Docker extension in Cursor, installing Docker Desktop is the easiest path:

### Quick Steps:
1. **Download**: https://www.docker.com/products/docker-desktop/
2. **Install**: Run the installer (takes 5-10 minutes)
3. **Start**: Open Docker Desktop, wait for it to start
4. **Run**: In PowerShell, type `docker compose up -d`
5. **Access**: Open http://localhost:3000/trading

**Total time: ~15 minutes**

---

## 🔄 Alternative: Install Python & Node.js

If you don't want Docker, install these instead:

### Python 3.12+
- Download: https://www.python.org/downloads/
- **Important**: Check "Add Python to PATH" during installation
- Restart terminal after installation

### Node.js 18+ (LTS)
- Download: https://nodejs.org/
- Installer adds to PATH automatically
- Restart terminal after installation

### Then Start Services:
**Terminal 1:**
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app:app --reload
```

**Terminal 2:**
```powershell
cd frontend
npm install
npm run dev
```

**Total time: ~20-30 minutes** (including downloads)

---

## 💡 My Recommendation

**Go with Docker Desktop** because:
- ✅ One installation instead of two
- ✅ Everything runs in containers (cleaner)
- ✅ Easy to start/stop with one command
- ✅ No need to manage Python/Node versions
- ✅ Works with your Cursor Docker extension

---

## ⚡ After Installation

Once Docker Desktop is installed and running:

```powershell
# Start everything
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f

# Stop everything
docker compose down
```

Then visit: **http://localhost:3000/trading** 🚀

