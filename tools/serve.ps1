$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$frontendDir = Join-Path $root "frontend"
$serveDir = Join-Path $PSScriptRoot ".serve"
$pidFile = Join-Path $serveDir "pids.json"

$backendUrl = "http://127.0.0.1:8000/docs"
$frontendUrl = "http://127.0.0.1:5500/"

function Test-Python($candidate) {
  try {
    & $candidate --version *> $null
    return $LASTEXITCODE -eq 0
  } catch {
    return $false
  }
}

function Find-Python {
  $candidates = @(
    (Join-Path $root ".venv\Scripts\python.exe"),
    "python"
  )

  foreach ($candidate in $candidates) {
    if (($candidate -eq "python") -or (Test-Path -LiteralPath $candidate)) {
      if (Test-Python $candidate) {
        return $candidate
      }
    }
  }

  return $null
}

function Test-HttpOk($url) {
  try {
    $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2
    return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400)
  } catch {
    return $false
  }
}

function Get-LogTail($path) {
  if (-not (Test-Path -LiteralPath $path)) {
    return "(log file has not been created yet)"
  }
  $tail = Get-Content -LiteralPath $path -Tail 20 -ErrorAction SilentlyContinue
  if (-not $tail) {
    return "(log file is empty)"
  }
  return ($tail -join "`n")
}

function Wait-HttpReady($name, $url, $process, $stderrLog) {
  $deadline = (Get-Date).AddSeconds(20)
  while ((Get-Date) -lt $deadline) {
    if (Test-HttpOk $url) {
      return
    }
    if ($process -and $process.HasExited) {
      $tail = Get-LogTail $stderrLog
      throw "$name exited before it became ready. Check $stderrLog.`n$tail"
    }
    Start-Sleep -Milliseconds 500
  }

  $tail = Get-LogTail $stderrLog
  throw "$name did not become ready at $url within 20 seconds. Check $stderrLog.`n$tail"
}

function Start-Server($name, $arguments, $workingDirectory, $stdoutLog, $stderrLog) {
  Write-Host "[serve] Starting $name..."
  return Start-Process `
    -FilePath $script:python `
    -ArgumentList $arguments `
    -WorkingDirectory $workingDirectory `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog `
    -WindowStyle Hidden `
    -PassThru
}

function Stop-StartedProcess($name, $process) {
  if ($process -and -not $process.HasExited) {
    Write-Host "[serve] Cleaning up $name process $($process.Id) after startup failure..."
    Stop-Process -Id $process.Id -ErrorAction SilentlyContinue
  }
}

New-Item -ItemType Directory -Force -Path $serveDir | Out-Null

$python = Find-Python
if ([string]::IsNullOrWhiteSpace($python)) {
  throw "No working Python found. Fix .venv or install Python, then rerun tools\serve.ps1."
}

$backendOut = Join-Path $serveDir "backend.out.log"
$backendErr = Join-Path $serveDir "backend.err.log"
$frontendOut = Join-Path $serveDir "frontend.out.log"
$frontendErr = Join-Path $serveDir "frontend.err.log"

$backendProcess = $null
$frontendProcess = $null

try {
  if (Test-HttpOk $backendUrl) {
    Write-Host "[serve] Backend already responds at $backendUrl; not starting a new backend."
  } else {
    $backendProcess = Start-Server "backend" @("-m", "uvicorn", "backend.main:app", "--port", "8000") $root $backendOut $backendErr
  }

  if (Test-HttpOk $frontendUrl) {
    Write-Host "[serve] Frontend already responds at $frontendUrl; not starting a new frontend."
  } else {
    $frontendProcess = Start-Server "frontend" @("-m", "http.server", "5500") $frontendDir $frontendOut $frontendErr
  }

  Wait-HttpReady "Backend" $backendUrl $backendProcess $backendErr
  Wait-HttpReady "Frontend" $frontendUrl $frontendProcess $frontendErr

  $state = [pscustomobject]@{
    started_at = (Get-Date).ToString("o")
    backend_pid = if ($backendProcess) { $backendProcess.Id } else { $null }
    frontend_pid = if ($frontendProcess) { $frontendProcess.Id } else { $null }
    backend_url = $backendUrl
    frontend_url = "http://localhost:5500/"
    logs = [pscustomobject]@{
      backend_stdout = $backendOut
      backend_stderr = $backendErr
      frontend_stdout = $frontendOut
      frontend_stderr = $frontendErr
    }
  }

  $state | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $pidFile -Encoding UTF8

  Write-Host ""
  Write-Host "[serve] ready"
  Write-Host "[serve] Backend docs: $backendUrl"
  Write-Host "[serve] Frontend: http://localhost:5500/"
  Write-Host "[serve] Logs and PIDs: $serveDir"
  Write-Host "[serve] Stop servers started by this helper with: tools\stop-serve.ps1"
} catch {
  Stop-StartedProcess "backend" $backendProcess
  Stop-StartedProcess "frontend" $frontendProcess
  Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
  throw
}
