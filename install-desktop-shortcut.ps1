# Create a desktop shortcut for PeachAlgo Coach
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Target = Join-Path $Root "start-dev.bat"
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "黄桃算法教练.lnk"

$Wsh = New-Object -ComObject WScript.Shell
$Shortcut = $Wsh.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $Target
$Shortcut.WorkingDirectory = $Root
$Shortcut.WindowStyle = 7  # minimized
$Shortcut.Description = "启动 PeachAlgo Coach（黄桃算法教练）"
# Prefer a browser-like system icon if available
$Shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,13"
$Shortcut.Save()

Write-Host "Desktop shortcut created:" -ForegroundColor Green
Write-Host "  $ShortcutPath"
Write-Host ""
Write-Host "Double-click it anytime to start the app and open the browser."
Write-Host ""
Write-Host "Optional — auto-start on Windows login:"
Write-Host "  1) Win+R, type: shell:startup"
Write-Host "  2) Copy the desktop shortcut into that folder"
Write-Host ""
pause
