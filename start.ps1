$ErrorActionPreference = "Continue"
$base = Split-Path -Parent $MyInvocation.MyCommand.Path

function Stop-Port([int]$port) {
    Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique |
        ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
}

Write-Host "[1/4] Stopping any old servers..." -ForegroundColor Cyan
Stop-Port 8000
Stop-Port 5173
Start-Sleep -Seconds 1

$py = Join-Path $base "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "ERROR: venv missing. Run first:  py -m venv backend\.venv  then:  backend\.venv\Scripts\python -m pip install -r backend\requirements.txt" -ForegroundColor Red
    exit 1
}
$npm = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
if (-not $npm) {
    Write-Host "ERROR: npm not found. Install Node.js first." -ForegroundColor Red
    exit 1
}

Write-Host "[2/4] Starting backend on http://127.0.0.1:8000 ..." -ForegroundColor Cyan
Start-Process -FilePath $py -ArgumentList "run.py" -WorkingDirectory (Join-Path $base "backend") -WindowStyle Hidden

Write-Host "[3/4] Starting frontend on http://localhost:5173 ..." -ForegroundColor Cyan
$nodeExe = (Get-Command node.exe -ErrorAction SilentlyContinue).Source
$viteJs = Join-Path $base "frontend\node_modules\vite\bin\vite.js"
if (-not $nodeExe -or -not (Test-Path $viteJs)) {
    Start-Process -FilePath $npm -ArgumentList @("run", "dev") -WorkingDirectory (Join-Path $base "frontend") -WindowStyle Hidden
} else {
    Start-Process -FilePath $nodeExe -ArgumentList ('"' + $viteJs + '"') -WorkingDirectory (Join-Path $base "frontend") -WindowStyle Hidden
}

Write-Host "[4/4] Starting servers... " -NoNewline -ForegroundColor Cyan

function Test-Port([int]$port) {
    return [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}

$okB = $false; $okF = $false
for ($i = 0; $i -lt 24; $i++) {
    Start-Sleep -Milliseconds 1500
    if (-not $okB) { $okB = Test-Port 8000 }
    if (-not $okF) { $okF = Test-Port 5173 }
    if ($okB -and $okF) { break }
}

if ($okB)  { Write-Host "  Backend  UP  -> http://127.0.0.1:8000/api/health" -ForegroundColor Green }
else       { Write-Host "  Backend  FAILED - open http://127.0.0.1:8000 to inspect" -ForegroundColor Red }
if ($okF)  { Write-Host "  Frontend UP  -> http://localhost:5173" -ForegroundColor Green; Start-Process "http://localhost:5173" }
else       { Write-Host "  Frontend FAILED - open http://localhost:5173 manually" -ForegroundColor Red }