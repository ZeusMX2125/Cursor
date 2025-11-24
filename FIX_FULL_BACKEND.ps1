# Fix Backend Installation - Full Functionality
# This installs all dependencies including PostgreSQL

Write-Host "Installing Backend with Full Functionality..." -ForegroundColor Green
Write-Host ""

cd backend

# Activate or create virtual environment
if (-not (Test-Path venv)) {
    Write-Host 'Creating virtual environment...' -ForegroundColor Yellow
    $pyCmd = if (Get-Command py -ErrorAction SilentlyContinue) { 'py' } elseif (Get-Command python -ErrorAction SilentlyContinue) { 'python' } else { 'python3' }
    & $pyCmd -m venv venv
}

& .\venv\Scripts\Activate.ps1

# Upgrade pip and setuptools
Write-Host 'Upgrading pip and setuptools...' -ForegroundColor Yellow
python -m pip install --upgrade pip setuptools wheel --quiet

# Clear pip cache
Write-Host 'Clearing pip cache...' -ForegroundColor Yellow
pip cache purge

# Install psycopg2-binary first with latest version that has wheels
Write-Host 'Installing psycopg2-binary (trying latest version)...' -ForegroundColor Yellow
pip install --upgrade --only-binary :all: psycopg2-binary

if ($LASTEXITCODE -ne 0) {
    Write-Host 'Trying without binary-only constraint...' -ForegroundColor Yellow
    pip install --upgrade --no-build-isolation psycopg2-binary
}

# Now install all other requirements
Write-Host 'Installing all other dependencies...' -ForegroundColor Yellow
pip install --no-cache-dir -r requirements.txt

Write-Host ""
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To start backend:" -ForegroundColor Cyan
Write-Host "  cd backend" -ForegroundColor White
Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "  uvicorn app:app --reload" -ForegroundColor White
Write-Host ""

