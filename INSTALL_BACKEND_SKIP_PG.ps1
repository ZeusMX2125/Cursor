# Install Backend Dependencies (Skip PostgreSQL for now)
# This allows you to see the UI while we fix the PostgreSQL issue

Write-Host "Installing Backend (without PostgreSQL)..." -ForegroundColor Green
Write-Host ""

cd backend

# Activate virtual environment
if (Test-Path venv) {
    & .\venv\Scripts\Activate.ps1
} else {
    Write-Host 'Creating virtual environment...' -ForegroundColor Yellow
    $pyCmd = if (Get-Command py -ErrorAction SilentlyContinue) { 'py' } elseif (Get-Command python -ErrorAction SilentlyContinue) { 'python' } else { 'python3' }
    & $pyCmd -m venv venv
    & .\venv\Scripts\Activate.ps1
}

# Upgrade pip
Write-Host 'Upgrading pip...' -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet

# Install minimal requirements (without PostgreSQL)
Write-Host 'Installing dependencies (skipping PostgreSQL)...' -ForegroundColor Yellow
pip install --no-cache-dir -r requirements-minimal.txt

Write-Host ""
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host "Backend can now start (without database features)." -ForegroundColor Cyan
Write-Host ""
Write-Host "To start backend:" -ForegroundColor Yellow
Write-Host "  cd backend" -ForegroundColor White
Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "  uvicorn app:app --reload" -ForegroundColor White
Write-Host ""

