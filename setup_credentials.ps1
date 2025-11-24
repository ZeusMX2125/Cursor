# Quick credential setup script
Write-Host "=== TopStepX Trading Bot Credential Setup ===" -ForegroundColor Cyan
Write-Host ""

$username = Read-Host "Enter your TopStepX Username"
$apiKey = Read-Host "Enter your TopStepX API Key" -AsSecureString
$apiKeyPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($apiKey)
)

$envContent = @"
TOPSTEPX_USERNAME=$username
TOPSTEPX_API_KEY=$apiKeyPlain
TOPSTEPX_BASE_URL=https://gateway.projectx.com/api

DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/topstepx_bot
REDIS_URL=redis://localhost:6379/0

LOG_LEVEL=INFO
TIMEZONE=America/Chicago
PAPER_TRADING_MODE=true
"@

Set-Content -Path "backend\.env" -Value $envContent -Encoding UTF8
Write-Host ""
Write-Host "✓ Credentials saved to backend/.env" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Start backend: cd backend && py -m uvicorn app:app --reload" -ForegroundColor White
Write-Host "2. Start frontend: cd frontend && npm run dev" -ForegroundColor White
Write-Host "3. Open browser: http://localhost:3000" -ForegroundColor White

