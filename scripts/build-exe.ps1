# Build a double-clickable desktop app:
#   dist/PeachAlgoCoach/PeachAlgoCoach.exe
#
# Requirements (once):
#   - Node.js / npm
#   - Python venv with backend deps
#   - pip install pyinstaller

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not (Test-Path (Join-Path $Root "backend"))) {
  # script lives in scripts/ → parent is repo root
  $Root = Split-Path -Parent $MyInvocation.MyCommand.Path
  if (Test-Path (Join-Path (Split-Path -Parent $Root) "backend")) {
    $Root = Split-Path -Parent $Root
  }
}
# Robust: walk up from this script until backend/ exists
$Probe = $PSScriptRoot
while ($Probe -and -not (Test-Path (Join-Path $Probe "backend\app\main.py"))) {
  $Parent = Split-Path -Parent $Probe
  if ($Parent -eq $Probe) { break }
  $Probe = $Parent
}
if (-not (Test-Path (Join-Path $Probe "backend\app\main.py"))) {
  throw "Cannot locate repo root from $PSScriptRoot"
}
$Root = $Probe
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Python = Join-Path $Backend ".venv\Scripts\python.exe"
$StaticOut = Join-Path $Backend "static"
$DistDir = Join-Path $Backend "dist\PeachAlgoCoach"

Write-Host "=== Build PeachAlgo Coach EXE ===" -ForegroundColor Cyan
Write-Host "Root: $Root"

if (-not (Test-Path $Python)) {
  throw "Missing backend venv python: $Python"
}

# 1) Frontend production build
Write-Host "`n[1/4] Building frontend..." -ForegroundColor Yellow
Push-Location $Frontend
try {
  if (-not (Test-Path "node_modules")) {
    npm install
  }
  npm run build
  if ($LASTEXITCODE -ne 0) { throw "frontend build failed" }
} finally {
  Pop-Location
}

$DistFrontend = Join-Path $Frontend "dist"
if (-not (Test-Path (Join-Path $DistFrontend "index.html"))) {
  throw "frontend dist missing index.html"
}

# 2) Copy static assets next to backend for packaging
Write-Host "`n[2/4] Copying static assets to backend/static ..." -ForegroundColor Yellow
if (Test-Path $StaticOut) {
  Remove-Item -Recurse -Force $StaticOut
}
Copy-Item -Recurse -Force $DistFrontend $StaticOut

# 3) Ensure packaging deps (PyInstaller + tray)
Write-Host "`n[3/4] Ensuring packaging deps..." -ForegroundColor Yellow
& $Python -m pip install -q -r (Join-Path $Backend "requirements-build.txt")
if ($LASTEXITCODE -ne 0) { throw "pip install packaging deps failed" }

# 4) Package
Write-Host "`n[4/4] Running PyInstaller..." -ForegroundColor Yellow
Push-Location $Backend
try {
  $spec = Join-Path $Backend "peachalgo_coach.spec"
  & $Python -m PyInstaller --noconfirm --clean $spec
  if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
} finally {
  Pop-Location
}

$Exe = Join-Path $DistDir "PeachAlgoCoach.exe"
if (-not (Test-Path $Exe)) {
  throw "Expected exe not found: $Exe"
}

# Desktop shortcut to the built exe
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "黄桃算法教练.lnk"
$Wsh = New-Object -ComObject WScript.Shell
$Shortcut = $Wsh.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $Exe
$Shortcut.WorkingDirectory = $DistDir
$Shortcut.WindowStyle = 1
$Shortcut.Description = "黄桃算法教练 (PeachAlgo Coach)"
$Shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,13"
$Shortcut.Save()

Write-Host ""
Write-Host "Build OK" -ForegroundColor Green
Write-Host "  EXE     : $Exe"
Write-Host "  Desktop : $ShortcutPath"
Write-Host ""
Write-Host "Double-click the desktop icon (or the exe):"
Write-Host "  - no console window"
Write-Host "  - system tray icon appears (peach circle)"
Write-Host "  - browser opens automatically"
Write-Host "  - tray menu: Open / Quit"
Write-Host "User data (SQLite) lives under %LOCALAPPDATA%\PeachAlgoCoach\"
Write-Host ""
