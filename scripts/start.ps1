param(
    [ValidateSet("local", "lan")]
    [string]$Mode = "local",
    [int]$Port = 0,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

if ($Port -le 0) {
    $Port = if ($env:SMART_PUMP_PORT) {
        [int]$env:SMART_PUMP_PORT
    } else {
        8501
    }
}

if ($env:SMART_PUMP_NO_BROWSER -eq "1") {
    $NoBrowser = $true
}

$BindAddress = if ($Mode -eq "lan") { "0.0.0.0" } else { "127.0.0.1" }
$RuntimeDir = Join-Path $ProjectRoot "runtime"
$PidFile = Join-Path $RuntimeDir "streamlit.pid"
New-Item -ItemType Directory -Path $RuntimeDir -Force | Out-Null

function Test-ServiceHealth {
    try {
        $response = Invoke-WebRequest `
            -UseBasicParsing `
            -Uri "http://127.0.0.1:$Port/_stcore/health" `
            -TimeoutSec 2
        return (
            $response.StatusCode -eq 200 -and
            $response.Content.Trim() -eq "ok"
        )
    } catch {
        return $false
    }
}

function Open-SystemPage {
    if (-not $NoBrowser) {
        Start-Process "http://localhost:$Port"
    }
}

if (Test-Path $PidFile) {
    $existingPid = [int](Get-Content $PidFile -Raw).Trim()
    if (Get-Process -Id $existingPid -ErrorAction SilentlyContinue) {
        if (Test-ServiceHealth) {
            Write-Host "The system is already running."
            Write-Host "Address: http://localhost:$Port"
            Open-SystemPage
            exit 0
        }
        Write-Host "Removing a stale process record..."
    }
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
}

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    $BasePython = $null
    $BaseArgs = @()

    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        & $pythonCommand.Source -c (
            "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
        ) >$null 2>&1
        if ($LASTEXITCODE -eq 0) {
            $BasePython = $pythonCommand.Source
        }
    }

    if (-not $BasePython) {
        $pyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
        if ($pyLauncher) {
            foreach ($version in @("3.13", "3.12", "3.11", "3.10")) {
                & $pyLauncher.Source "-$version" -c (
                    "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
                ) >$null 2>&1
                if ($LASTEXITCODE -eq 0) {
                    $BasePython = $pyLauncher.Source
                    $BaseArgs = @("-$version")
                    break
                }
            }
        }
    }

    if (-not $BasePython) {
        throw (
            "Python 3.10 or newer was not found. " +
            "Install Python from https://www.python.org/downloads/ " +
            "and enable 'Add Python to PATH'."
        )
    }

    Write-Host "Creating the local Python environment..."
    & $BasePython @BaseArgs -m venv (Join-Path $ProjectRoot ".venv")
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create the Python virtual environment."
    }
}

& $VenvPython -c "import streamlit, pandas, plotly, reportlab" >$null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing required packages. This can take several minutes..."
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install `
        --index-url https://pypi.org/simple `
        -r (Join-Path $ProjectRoot "requirements-lock.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency installation failed. Check the network connection."
    }
}

if (Test-ServiceHealth) {
    Write-Host "Port $Port already has a healthy service."
    Write-Host "Address: http://localhost:$Port"
    Open-SystemPage
    exit 0
}

$StreamlitArgs = @(
    "-m",
    "streamlit",
    "run",
    "app.py",
    "--server.headless=true",
    "--server.address=$BindAddress",
    "--server.port=$Port",
    "--browser.gatherUsageStats=false",
    "--server.fileWatcherType=none"
)

Write-Host "Starting the system on port $Port..."
$Process = Start-Process `
    -FilePath $VenvPython `
    -ArgumentList $StreamlitArgs `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Hidden `
    -PassThru

Set-Content -LiteralPath $PidFile -Value $Process.Id -Encoding ascii

$Healthy = $false
for ($index = 0; $index -lt 40; $index++) {
    Start-Sleep -Milliseconds 500
    if (Test-ServiceHealth) {
        $Healthy = $true
        break
    }
}

if (-not $Healthy) {
    & taskkill.exe /PID $Process.Id /T /F >$null 2>&1
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
    throw (
        "The service did not become healthy. " +
        "Check whether port $Port is already in use."
    )
}

Write-Host ""
Write-Host "System started successfully."
Write-Host "Address: http://localhost:$Port"
if ($Mode -eq "lan") {
    Write-Host "LAN mode is enabled. Use http://YOUR-IP:$Port from other devices."
}
Write-Host "Run the stop script to pause the service."
Open-SystemPage
