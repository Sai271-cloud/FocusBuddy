$ErrorActionPreference = "Stop"

$serveDir = Join-Path $PSScriptRoot ".serve"
$pidFile = Join-Path $serveDir "pids.json"

if (-not (Test-Path -LiteralPath $pidFile)) {
  Write-Host "[serve] No PID file found at $pidFile. Nothing to stop."
  exit 0
}

$state = Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json

$targets = @(
  [pscustomobject]@{ Name = "backend"; Pid = $state.backend_pid },
  [pscustomobject]@{ Name = "frontend"; Pid = $state.frontend_pid }
)

foreach ($target in $targets) {
  if ($null -eq $target.Pid) {
    Write-Host "[serve] $($target.Name) was already running before serve.ps1; leaving it alone."
    continue
  }

  $pidValue = [int]$target.Pid
  $process = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
  if ($null -eq $process) {
    Write-Host "[serve] $($target.Name) process $pidValue is already stopped."
    continue
  }

  Write-Host "[serve] Stopping $($target.Name) process $pidValue..."
  Stop-Process -Id $pidValue -ErrorAction SilentlyContinue
}

Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
Write-Host "[serve] Removed $pidFile."
