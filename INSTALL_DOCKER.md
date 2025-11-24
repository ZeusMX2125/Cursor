# Install Docker Desktop - Quick Guide

## Why You Need Docker Desktop

The Docker extension in Cursor is just a UI tool - you still need **Docker Desktop** installed and running to actually execute Docker commands.

## Installation Steps

### 1. Download Docker Desktop
Go to: **https://www.docker.com/products/docker-desktop/**

Click "Download for Windows"

### 2. Install Docker Desktop
1. Run the installer
2. Follow the installation wizard
3. **Important**: Check "Use WSL 2 instead of Hyper-V" (if prompted)
4. Restart your computer when prompted

### 3. Start Docker Desktop
1. Open Docker Desktop from Start Menu
2. Wait for it to start (whale icon in system tray)
3. First start may take 2-3 minutes

### 4. Verify Installation
Open PowerShell and run:
```powershell
docker --version
docker compose version
```

If both commands show version numbers, you're ready!

### 5. Start the Trading Bot
```powershell
docker compose up -d
```

Then visit: **http://localhost:3000/trading**

## System Requirements

- Windows 10 64-bit: Pro, Enterprise, or Education (Build 19041 or higher)
- OR Windows 11 64-bit
- WSL 2 feature enabled
- Virtualization enabled in BIOS

## If Installation Fails

**WSL 2 not installed?**
```powershell
wsl --install
```
Then restart your computer and try Docker Desktop again.

## After Installation

Once Docker Desktop is installed and running, you can use the Cursor Docker extension to manage containers, or use the command line.

---

## Alternative: Install Python & Node.js Instead

If you prefer not to use Docker, you can install:
- **Python 3.12+**: https://www.python.org/downloads/
- **Node.js 18+**: https://nodejs.org/

Then run the services manually (see QUICK_FIX.md)


