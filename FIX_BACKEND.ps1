# Fix Backend Installation Issues
# This script fixes common pip installation problems

Write-Host "Fixing Backend Installation..." -ForegroundColor Green
Write-Host ""

cd backend

# Check if venv exists
if (-not (Test-Path venv)) {
    Write-Host 'Creating virtual environment...' -ForegroundColor Yellow
    $pyCmd = if (Get-Command py -ErrorAction SilentlyContinue) { 'py' } elseif (Get-Command python -ErrorAction SilentlyContinue) { 'python' } else { 'python3' }
    & $pyCmd -m venv venv
}

# Activate virtual environment
Write-Host 'Activating virtual environment...' -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host 'Upgrading pip...' -ForegroundColor Yellow
python -m pip install --upgrade pip

# Clear pip cache
Write-Host 'Clearing pip cache...' -ForegroundColor Yellow
pip cache purge

# Install requirements with no cache
Write-Host 'Installing dependencies (this may take a few minutes)...' -ForegroundColor Yellow
pip install --no-cache-dir -r requirements.txt

Write-Host ""
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host "You can now start the backend with:" -ForegroundColor Cyan
Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "  uvicorn app:app --reload" -ForegroundColor White
Write-Host ""

