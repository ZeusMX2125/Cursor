# Start Frontend Server
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
cd frontend
if (-not (Test-Path node_modules)) {
    Write-Host 'Installing dependencies...' -ForegroundColor Yellow
    npm install
}
Write-Host 'Frontend starting on http://localhost:3000' -ForegroundColor Green
Write-Host 'ALGOX Interface: http://localhost:3000/trading' -ForegroundColor Yellow
npm run dev

