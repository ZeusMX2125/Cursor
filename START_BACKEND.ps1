# Start Backend Server
cd backend
if (-not (Test-Path venv)) {
    Write-Host 'Creating virtual environment...' -ForegroundColor Yellow
    $pyCmd = if (Get-Command py -ErrorAction SilentlyContinue) { 'py' } elseif (Get-Command python -ErrorAction SilentlyContinue) { 'python' } else { 'python3' }
    & $pyCmd -m venv venv
}

# Activate virtual environment
& .\venv\Scripts\Activate.ps1

# Upgrade pip first
Write-Host 'Upgrading pip...' -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet

# Install requirements with no cache to avoid build issues
Write-Host 'Installing dependencies...' -ForegroundColor Yellow
pip install --no-cache-dir -r requirements.txt

Write-Host 'Backend starting on http://localhost:8000' -ForegroundColor Green
Write-Host 'API Docs: http://localhost:8000/docs' -ForegroundColor Cyan
uvicorn app:app --reload --host 0.0.0.0 --port 8000

