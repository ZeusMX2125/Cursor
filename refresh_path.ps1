# Simple script to refresh PATH and check Node.js
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
Write-Host "PATH refreshed!" -ForegroundColor Green
Write-Host ""
Write-Host "Node.js version:" -ForegroundColor Cyan
node --version
Write-Host ""
Write-Host "npm version:" -ForegroundColor Cyan
npm --version

