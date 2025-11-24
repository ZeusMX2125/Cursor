# Start TopStepX Trading Bot
# Run with: powershell -ExecutionPolicy Bypass -File .\START_BOT.ps1

Write-Host "=== Starting TopStepX Trading Bot ===" -ForegroundColor Cyan
Write-Host ""

# Check if credentials are set
$envFile = "backend\.env"
if (-not (Test-Path $envFile)) {
    Write-Host "ERROR: backend/.env file not found!" -ForegroundColor Red
    Write-Host "Run: .\setup_credentials.ps1" -ForegroundColor Yellow
    exit 1
}

$envContent = Get-Content $envFile -Raw
if ($envContent -match "your_topstepx_username|your_topstepx_api_key") {
    Write-Host "WARNING: Credentials not configured!" -ForegroundColor Yellow
    Write-Host "Please edit backend/.env with your TopStepX credentials" -ForegroundColor Yellow
    Write-Host "Or run: .\setup_credentials.ps1" -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne "y") {
        exit 1
    }
}

# Start backend
Write-Host "Starting backend server..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\backend'; py -m uvicorn app:app --reload --host 0.0.0.0 --port 8000"

Start-Sleep -Seconds 3

# Start frontend
Write-Host "Starting frontend server..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\frontend'; npm run dev"

Write-Host ""
Write-Host "✓ Servers starting..." -ForegroundColor Green
Write-Host ""
Write-Host "Backend: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to open browser..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

Start-Process "http://localhost:3000"

