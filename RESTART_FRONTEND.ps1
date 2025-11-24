# Restart Frontend with ALGOX Interface
# This script fixes execution policy and clears cache

Write-Host "Restarting Frontend Server..." -ForegroundColor Green
Write-Host ""

# Set execution policy for current process
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force

# Refresh PATH
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

cd frontend

# Clear Next.js cache
Write-Host "Clearing Next.js cache..." -ForegroundColor Yellow
Remove-Item -Recurse -Force .next -ErrorAction SilentlyContinue

Write-Host "Starting frontend dev server..." -ForegroundColor Green
Write-Host "After it starts, visit: http://localhost:3000/trading" -ForegroundColor Cyan
Write-Host ""

# Start dev server
npm run dev

