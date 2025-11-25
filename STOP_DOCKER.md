# Stopping Docker Containers

If you're using `.bat` files to run the backend and frontend, you may need to stop Docker containers that are blocking ports 8000 or 3000.

## Quick Stop (Recommended)

Run the `stop.bat` script - it now automatically stops Docker containers:

```batch
stop.bat
```

This will stop:
- Docker containers (cursor-backend-1, cursor-frontend-1, topstepx-engine, etc.)
- Direct processes on ports 8000 and 3000
- Python uvicorn processes
- Node.js processes

## Manual Docker Commands

If you prefer to stop Docker manually:

### Stop All Docker Compose Services

```powershell
docker compose down
```

This stops and removes all containers defined in `docker-compose.yml`.

### Stop Specific Containers

```powershell
# Stop containers by name
docker stop cursor-backend-1 cursor-frontend-1 topstepx-engine

# Or stop all containers
docker stop $(docker ps -q)
```

### List Running Containers

```powershell
# See all running containers
docker ps

# See containers using ports 8000 or 3000
docker ps --format "table {{.Names}}\t{{.Ports}}" | findstr ":8000\|:3000"
```

### Remove Stopped Containers

```powershell
# Remove all stopped containers
docker container prune

# Remove specific container
docker rm cursor-backend-1
```

## Why Stop Docker?

When using `.bat` files:
- Docker containers may be running old code
- Docker containers block ports 8000 and 3000
- `.bat` files can't start if ports are in use
- You want to run the latest code directly (not in Docker)

## Verify Ports Are Free

After stopping Docker, verify ports are free:

```powershell
# Check port 8000
netstat -ano | findstr ":8000"

# Check port 3000
netstat -ano | findstr ":3000"
```

If nothing is returned, the ports are free and you can run `start.bat`.

## Troubleshooting

### "Port already in use" error

1. Run `stop.bat` to stop everything
2. Wait 5 seconds
3. Check ports: `netstat -ano | findstr ":8000 :3000"`
4. If still in use, manually kill the process:
   ```powershell
   # Find PID using port 8000
   netstat -ano | findstr ":8000"
   # Kill it (replace <PID> with actual number)
   taskkill /F /PID <PID>
   ```

### Docker containers keep restarting

If containers restart automatically:
```powershell
# Stop and remove containers
docker compose down

# Or stop specific container
docker stop topstepx-engine
docker rm topstepx-engine
```

### Can't find Docker

If Docker commands don't work:
- Docker Desktop may not be installed
- Docker Desktop may not be running
- Docker may not be in your PATH

In this case, just use `stop.bat` - it will skip Docker and stop direct processes.

