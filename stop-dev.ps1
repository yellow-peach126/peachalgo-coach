Write-Host "Looking for PeachAlgo / uvicorn / vite processes..."

# Kill known child first if present
try { Stop-Process -Id 22204 -Force -ErrorAction SilentlyContinue } catch {}

$targets = Get-CimInstance Win32_Process | Where-Object {
  $cmd = $_.CommandLine
  if (-not $cmd) { return $false }
  return (
    $cmd -match 'uvicorn' -or
    $cmd -match 'app\.main:app' -or
    $cmd -match 'leetcode-coach' -or
    $cmd -match 'peachalgo' -or
    $cmd -match 'multiprocessing\.spawn' -or
    ($cmd -match 'vite' -and ($cmd -match '5173' -or $cmd -match 'leetcode-coach' -or $cmd -match 'peachalgo'))
  )
}

if (-not $targets) {
  Write-Host "No matching process command lines found."
} else {
  foreach ($proc in $targets) {
    Write-Host ("Killing PID {0}: {1}" -f $proc.ProcessId, $proc.CommandLine)
    try {
      Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
    } catch {
      & taskkill.exe /PID $proc.ProcessId /F /T 2>$null | Out-Host
    }
  }
}

# Also try owning PIDs of the ports
foreach ($port in 8000, 5173) {
  $owners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique
  foreach ($owner in $owners) {
    if ($owner -and $owner -gt 0) {
      Write-Host ("Port {0} owner PID {1}" -f $port, $owner)
      try { Stop-Process -Id $owner -Force -ErrorAction SilentlyContinue } catch {}
      & taskkill.exe /PID $owner /F /T 2>$null | Out-Host
    }
  }
}

Start-Sleep -Seconds 2

Write-Host "--- remaining python with relevant cmdline ---"
Get-CimInstance Win32_Process -Filter "name='python.exe'" | ForEach-Object {
  if ($_.CommandLine -match 'uvicorn|app\.main|leetcode-coach|multiprocessing') {
    Write-Host ("still alive {0}: {1}" -f $_.ProcessId, $_.CommandLine)
  }
}

Write-Host "--- ports ---"
$left = netstat -ano -p tcp | Select-String -Pattern ':8000|:5173' | Select-String -Pattern 'LISTENING'
if ($left) { $left | ForEach-Object { Write-Host $_.Line } } else { Write-Host "ports free" }

try {
  $health = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 2 -UseBasicParsing
  Write-Host ("backend still responds: " + $health.Content)
} catch {
  Write-Host "backend not responding (good)"
}
