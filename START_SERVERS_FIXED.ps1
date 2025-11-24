# Fixed PowerShell script to start TopstepX Trading Bot servers
# This version bypasses execution policy issues

Write-Host "Starting TopstepX Trading Bot..." -ForegroundColor Green
Write-Host ""

# Check Python
Write-Host "Checking Python..." -ForegroundColor Yellow
$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCmd = "py"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonCmd = "python3"
}

if ($pythonCmd) {
    try {
        $pythonVersion = & $pythonCmd --version 2>&1
        Write-Host "Python found: $pythonVersion" -ForegroundColor Green
    } catch {
        Write-Host "ERROR: Python not found!" -ForegroundColor Red
        Write-Host "Please install Python 3.12+ from https://www.python.org/" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "ERROR: Python not found!" -ForegroundColor Red
    Write-Host "Please install Python 3.12+ from https://www.python.org/" -ForegroundColor Yellow
    exit 1
}

# Check Node.js
Write-Host "Checking Node.js..." -ForegroundColor Yellow
if (Get-Command node -ErrorAction SilentlyContinue) {
    try {
        $nodeVersion = node --version 2>&1
        Write-Host "Node.js found: $nodeVersion" -ForegroundColor Green
    } catch {
        Write-Host "ERROR: Node.js not found!" -ForegroundColor Red
        Write-Host "Please install Node.js from https://nodejs.org/" -ForegroundColor Yellow
        Write-Host "See INSTALL_NODEJS.md for detailed instructions." -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "ERROR: Node.js not found!" -ForegroundColor Red
    Write-Host "Please install Node.js from https://nodejs.org/" -ForegroundColor Yellow
    Write-Host "See INSTALL_NODEJS.md for detailed instructions." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Starting Backend Server..." -ForegroundColor Cyan
Write-Host ""

# Start Backend
$backendScript = @"
cd backend
if (-not (Test-Path venv)) {
    Write-Host 'Creating virtual environment...'
    $pyCmd = if (Get-Command py -ErrorAction SilentlyContinue) { 'py' } elseif (Get-Command python -ErrorAction SilentlyContinue) { 'python' } else { 'python3' }
    & $pyCmd -m venv venv
}
& .\venv\Scripts\Activate.ps1
pip install -q -r requirements.txt
Write-Host 'Backend starting on http://localhost:8000' -ForegroundColor Green
uvicorn app:app --reload --host 0.0.0.0 --port 8000
"@

Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $backendScript

Write-Host "Waiting 5 seconds for backend to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

Write-Host ""
Write-Host "Starting Frontend Server..." -ForegroundColor Cyan
Write-Host ""

# Start Frontend
$frontendScript = @"
cd frontend
if (-not (Test-Path node_modules)) {
    Write-Host 'Installing dependencies...'
    npm install
}
Write-Host 'Frontend starting on http://localhost:3000' -ForegroundColor Green
npm run dev
"@

Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $frontendScript

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Servers are starting!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Backend: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "NEW ALGOX INTERFACE: http://localhost:3000/trading" -ForegroundColor Yellow
Write-Host ""
Write-Host "Wait 10-15 seconds for servers to fully start..." -ForegroundColor Yellow
Write-Host "Keep both PowerShell windows open!" -ForegroundColor Yellow
Write-Host ""

