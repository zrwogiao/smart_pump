param(
    [int]$Port = 0
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$RuntimeDir = Join-Path $ProjectRoot "runtime"
$PidFile = Join-Path $RuntimeDir "streamlit.pid"

if ($Port -le 0) {
    $Port = if ($env:SMART_PUMP_PORT) {
        [int]$env:SMART_PUMP_PORT
    } else {
        8501
    }
}

if (-not (Test-Path $PidFile)) {
    Write-Host "The system is not running, or it was not started by start.bat."
    exit 0
}

$ProcessId = [int](Get-Content $PidFile -Raw).Trim()
$Process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue

$TargetIds = New-Object System.Collections.Generic.HashSet[int]
if ($Process) {
    [void]$TargetIds.Add($ProcessId)
}

# The virtual-environment launcher can create a second Python child process.
# Stop the recorded process and the process listening on the requested port.
$NetstatLines = & netstat.exe -ano 2>$null
foreach ($line in $NetstatLines) {
    if ($line -match "^\s*TCP\s+\S+:$Port\s+\S+\s+LISTENING\s+(\d+)\s*$") {
        [void]$TargetIds.Add([int]$Matches[1])
    }
}

if ($TargetIds.Count -gt 0) {
    Write-Host "Stopping the system..."
    foreach ($targetId in $TargetIds) {
        if ($targetId -le 0) {
            continue
        }
        Stop-Process -Id $targetId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 1
}

Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue

$StillHealthy = $false
try {
    $response = Invoke-WebRequest `
        -UseBasicParsing `
        -Uri "http://127.0.0.1:$Port/_stcore/health" `
        -TimeoutSec 2
    $StillHealthy = $response.StatusCode -eq 200
} catch {
    $StillHealthy = $false
}

if ($StillHealthy) {
    Write-Host "The recorded process was stopped, but port $Port is still responding."
    Write-Host "Another instance may be using this port."
} else {
    Write-Host "The system has been paused."
}
