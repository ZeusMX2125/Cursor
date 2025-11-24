# PowerShell script to start Docker services

Write-Host "Starting TopstepX Trading Bot with Docker..." -ForegroundColor Green
Write-Host ""

# Check if Docker is available
Write-Host "Checking Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version 2>&1
    Write-Host "Docker found: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please:" -ForegroundColor Yellow
    Write-Host "1. Install Docker Desktop from https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
    Write-Host "2. Start Docker Desktop and wait for it to fully start" -ForegroundColor Yellow
    Write-Host "3. Restart this PowerShell window" -ForegroundColor Yellow
    Write-Host "4. Run this script again" -ForegroundColor Yellow
    exit 1
}

# Check if Docker Desktop is running
Write-Host "Checking if Docker Desktop is running..." -ForegroundColor Yellow
try {
    docker ps 2>&1 | Out-Null
    Write-Host "Docker Desktop is running!" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker Desktop is not running!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please start Docker Desktop and wait for it to fully start." -ForegroundColor Yellow
    Write-Host "Look for the whale icon in your system tray." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Starting services with Docker Compose..." -ForegroundColor Cyan
Write-Host ""

# Start services
docker compose up -d

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Services started successfully!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Waiting 10 seconds for services to initialize..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    
    Write-Host ""
    Write-Host "Services Status:" -ForegroundColor Cyan
    docker compose ps
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Access the interface:" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Backend API:  http://localhost:8000" -ForegroundColor Cyan
    Write-Host "API Docs:     http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host "Frontend:     http://localhost:3000" -ForegroundColor Cyan
    Write-Host "Trading:      http://localhost:3000/trading" -ForegroundColor Cyan -BackgroundColor DarkGreen
    Write-Host ""
    Write-Host "To view logs: docker compose logs -f" -ForegroundColor Yellow
    Write-Host "To stop:      docker compose down" -ForegroundColor Yellow
    Write-Host ""
    
    # Open browser
    Write-Host "Opening browser..." -ForegroundColor Yellow
    Start-Process "http://localhost:3000/trading"
} else {
    Write-Host ""
    Write-Host "ERROR: Failed to start services!" -ForegroundColor Red
    Write-Host "Check the error messages above." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Common issues:" -ForegroundColor Yellow
    Write-Host "- Docker Desktop not fully started" -ForegroundColor Yellow
    Write-Host "- Ports 3000 or 8000 already in use" -ForegroundColor Yellow
    Write-Host "- Insufficient Docker resources" -ForegroundColor Yellow
}


