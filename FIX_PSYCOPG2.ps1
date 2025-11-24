# Fix psycopg2-binary installation issue
# This tries multiple methods to install psycopg2-binary

Write-Host "Fixing psycopg2-binary installation..." -ForegroundColor Green
Write-Host ""

cd backend
& .\venv\Scripts\Activate.ps1

Write-Host "Method 1: Installing from wheel directly..." -ForegroundColor Yellow
pip install --only-binary :all: psycopg2-binary==2.9.9

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Method 2: Installing latest version..." -ForegroundColor Yellow
    pip install --only-binary :all: psycopg2-binary
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "Method 3: Installing without binary check..." -ForegroundColor Yellow
        pip install --no-build-isolation psycopg2-binary==2.9.9
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host ""
            Write-Host "ERROR: Could not install psycopg2-binary" -ForegroundColor Red
            Write-Host "You can skip PostgreSQL for now and use requirements-minimal.txt" -ForegroundColor Yellow
            exit 1
        }
    }
}

Write-Host ""
Write-Host "psycopg2-binary installed successfully!" -ForegroundColor Green
Write-Host "You can now install the rest of the requirements:" -ForegroundColor Cyan
Write-Host "  pip install -r requirements.txt" -ForegroundColor White
Write-Host ""

