# Stop TopStepX Trading Bot
# Run with: powershell -ExecutionPolicy Bypass -File .\STOP_BOT.ps1

Write-Host "=== Stopping TopStepX Trading Bot ===" -ForegroundColor Cyan
Write-Host ""

# Function to kill process on a port
function Stop-ProcessOnPort {
    param([int]$Port)
    
    $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if ($connections) {
        foreach ($conn in $connections) {
            $pid = $conn.OwningProcess
            if ($pid) {
                $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
                if ($proc) {
                    Write-Host "Stopping process $pid ($($proc.ProcessName)) on port $Port" -ForegroundColor Yellow
                    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                }
            }
        }
    }
}

# Stop backend (port 8000)
Write-Host "Stopping backend server (port 8000)..." -ForegroundColor Yellow
Stop-ProcessOnPort -Port 8000

# Stop frontend (port 3000)
Write-Host "Stopping frontend server (port 3000)..." -ForegroundColor Yellow
Stop-ProcessOnPort -Port 3000

# Also try to kill by process name
Write-Host "Cleaning up any remaining processes..." -ForegroundColor Yellow
Get-Process | Where-Object { 
    $_.ProcessName -eq "node" -and $_.CommandLine -like "*npm*dev*" 
} | Stop-Process -Force -ErrorAction SilentlyContinue

Get-Process | Where-Object { 
    $_.ProcessName -eq "python" -or $_.ProcessName -eq "py" 
} | Where-Object {
    $_.CommandLine -like "*uvicorn*"
} | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "✓ Servers stopped" -ForegroundColor Green
Write-Host ""

