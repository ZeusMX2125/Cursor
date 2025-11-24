# Docker Setup Instructions

## If Docker Desktop is Installed

### Step 1: Start Docker Desktop
1. Open **Docker Desktop** from Start Menu
2. Wait until it shows "Docker Desktop is running" (whale icon in system tray)
3. This may take 1-2 minutes on first start

### Step 2: Verify Docker is Working
Open PowerShell and run:
```powershell
docker --version
docker compose version
```

If these commands work, proceed to Step 3.

### Step 3: Start the Services
```powershell
docker compose up -d
```

This will:
- Start PostgreSQL database
- Start Redis cache
- Start Backend API (port 8000)
- Start Frontend (port 3000)

### Step 4: Check Status
```powershell
docker compose ps
```

You should see all 4 services running.

### Step 5: Access the Interface
Open your browser to: **http://localhost:3000/trading**

## If Docker Desktop is NOT Installed

Download and install from: https://www.docker.com/products/docker-desktop/

After installation:
1. Restart your computer (recommended)
2. Start Docker Desktop
3. Wait for it to fully start
4. Run the commands above

## Troubleshooting

### Docker commands not found
- **Solution**: Restart PowerShell/terminal after installing Docker Desktop
- Or add Docker to PATH manually

### Docker Desktop won't start
- Check Windows WSL 2 is installed (required for Docker Desktop)
- Update Docker Desktop to latest version
- Check system requirements

### Ports already in use
```powershell
# Stop existing containers
docker compose down

# Or stop specific service
docker compose stop frontend
docker compose stop backend
```

### View Logs
```powershell
# All services
docker compose logs

# Specific service
docker compose logs frontend
docker compose logs backend
```

### Stop Services
```powershell
docker compose down
```

### Restart Services
```powershell
docker compose restart
```

## Quick Commands Reference

```powershell
# Start everything
docker compose up -d

# Stop everything
docker compose down

# View logs
docker compose logs -f

# Check status
docker compose ps

# Rebuild after code changes
docker compose up -d --build
```


