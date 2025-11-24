# Fix asyncpg installation for Python 3.13
# Try installing latest version that might have Python 3.13 support

Write-Host "Fixing asyncpg installation..." -ForegroundColor Green
Write-Host ""

cd backend
& .\venv\Scripts\Activate.ps1

Write-Host "Trying to install latest asyncpg..." -ForegroundColor Yellow
pip install --upgrade asyncpg

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "asyncpg doesn't support Python 3.13 yet." -ForegroundColor Red
    Write-Host "Trying pre-release version..." -ForegroundColor Yellow
    pip install --pre asyncpg
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "ERROR: asyncpg cannot be installed on Python 3.13" -ForegroundColor Red
        Write-Host "Options:" -ForegroundColor Yellow
        Write-Host "  1. Use Python 3.12 instead" -ForegroundColor White
        Write-Host "  2. Wait for asyncpg to support Python 3.13" -ForegroundColor White
        Write-Host "  3. Use psycopg2-binary only (asyncpg is optional for async PostgreSQL)" -ForegroundColor White
        exit 1
    }
}

Write-Host ""
Write-Host "asyncpg installed successfully!" -ForegroundColor Green
Write-Host ""

