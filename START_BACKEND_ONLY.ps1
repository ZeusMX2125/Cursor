# Start Backend Only (for testing while Node.js is being installed)

Write-Host "Starting Backend Server Only..." -ForegroundColor Green
Write-Host ""

# Check Python
$pythonCmd = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCmd = "py"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonCmd = "python3"
}

if (-not $pythonCmd) {
    Write-Host "ERROR: Python not found!" -ForegroundColor Red
    Write-Host "Please install Python 3.12+ from https://www.python.org/" -ForegroundColor Yellow
    exit 1
}

Write-Host "Using Python: $pythonCmd" -ForegroundColor Cyan
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
Write-Host 'API Docs: http://localhost:8000/docs' -ForegroundColor Cyan
uvicorn app:app --reload --host 0.0.0.0 --port 8000
"@

Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $backendScript

Write-Host "Backend server is starting in a new window..." -ForegroundColor Green
Write-Host "Backend API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "NOTE: Frontend requires Node.js to be installed." -ForegroundColor Yellow
Write-Host "See INSTALL_NODEJS.md for installation instructions." -ForegroundColor Yellow
Write-Host ""

