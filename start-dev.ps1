# PeachAlgo Coach — one-click local launcher
# Double-click start-dev.bat, or run: powershell -File start-dev.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$Python = Join-Path $BackendDir ".venv\Scripts\python.exe"
$Npm = "npm"
$BackendUrl = "http://127.0.0.1:8000"
$FrontendUrl = "http://127.0.0.1:5173"
$HealthUrl = "$BackendUrl/api/health"

function Test-PortListening([int]$Port) {
  try {
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return $null -ne $conn
  } catch {
    return $false
  }
}

function Wait-HttpOk([string]$Url, [int]$TimeoutSec = 40) {
  $deadline = (Get-Date).AddSeconds($TimeoutSec)
  while ((Get-Date) -lt $deadline) {
    try {
      $resp = Invoke-WebRequest -Uri $Url -TimeoutSec 2 -UseBasicParsing
      if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) {
        return $true
      }
    } catch {
      Start-Sleep -Milliseconds 500
    }
  }
  return $false
}

Write-Host "=== PeachAlgo Coach ===" -ForegroundColor Cyan
Write-Host "Project: $Root"

if (-not (Test-Path $Python)) {
  Write-Host "ERROR: backend venv not found at $Python" -ForegroundColor Red
  Write-Host "Run once:"
  Write-Host "  cd backend"
  Write-Host "  python -m venv .venv"
  Write-Host "  .\.venv\Scripts\activate"
  Write-Host "  pip install -r requirements.txt"
  pause
  exit 1
}

if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
  Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
  Push-Location $FrontendDir
  try {
    & $Npm install
    if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
  } finally {
    Pop-Location
  }
}

# Start backend if needed
if (Wait-HttpOk $HealthUrl 2) {
  Write-Host "Backend already running on $BackendUrl" -ForegroundColor Green
} else {
  Write-Host "Starting backend on port 8000..." -ForegroundColor Yellow
  $backendCmd = "Set-Location -LiteralPath '$BackendDir'; & '$Python' -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
  Start-Process -FilePath "powershell.exe" -WindowStyle Minimized -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-Command", $backendCmd
  )
  if (-not (Wait-HttpOk $HealthUrl 40)) {
    Write-Host "ERROR: backend did not become healthy at $HealthUrl" -ForegroundColor Red
    pause
    exit 1
  }
  Write-Host "Backend ready." -ForegroundColor Green
}

# Start frontend if needed
$frontendReady = $false
try {
  $front = Invoke-WebRequest -Uri $FrontendUrl -TimeoutSec 2 -UseBasicParsing
  if ($front.StatusCode -eq 200) { $frontendReady = $true }
} catch {}

if ($frontendReady) {
  Write-Host "Frontend already running on $FrontendUrl" -ForegroundColor Green
} else {
  Write-Host "Starting frontend on port 5173..." -ForegroundColor Yellow
  $frontendCmd = "Set-Location -LiteralPath '$FrontendDir'; npm run dev -- --host 127.0.0.1 --port 5173"
  Start-Process -FilePath "powershell.exe" -WindowStyle Minimized -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-Command", $frontendCmd
  )
  if (-not (Wait-HttpOk $FrontendUrl 40)) {
    Write-Host "ERROR: frontend did not become ready at $FrontendUrl" -ForegroundColor Red
    pause
    exit 1
  }
  Write-Host "Frontend ready." -ForegroundColor Green
}

Write-Host "Opening browser: $FrontendUrl" -ForegroundColor Cyan
Start-Process $FrontendUrl

Write-Host ""
Write-Host "Done. Keep the minimized PowerShell windows open while using the app." -ForegroundColor Green
Write-Host "To stop later, run stop-dev.ps1 or double-click stop-dev.bat"
Write-Host ""
Start-Sleep -Seconds 2
