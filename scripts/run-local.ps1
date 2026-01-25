param(
    [switch]$SkipInfra,
    [switch]$SkipBackend,
    [switch]$SkipWebsocket,
    [switch]$SkipFrontend,
    [switch]$Detach
)

$ErrorActionPreference = 'Stop'

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Write-Error "Required command not found: $Name"
    }
}

if (-not $SkipInfra) {
    Require-Command docker
}

if (-not $SkipFrontend) {
    Require-Command node
    Require-Command pnpm
}

. "$PSScriptRoot\load-ports.ps1"

$backendPython = $null
if (-not ($SkipBackend -and $SkipWebsocket)) {
    $backendPython = & "$PSScriptRoot\backend-python.ps1" -EnsureDeps
}

if (-not $SkipInfra) {
    & "$PSScriptRoot\dev-up.ps1"
}

$processes = @()
$backendDir = (Resolve-Path "$PSScriptRoot\..\backend").Path
$frontendDir = (Resolve-Path "$PSScriptRoot\..\frontend").Path
$apiPort = if ($env:API_PORT) { $env:API_PORT } else { "8000" }
$wsPort = if ($env:WS_PORT) { $env:WS_PORT } else { "8002" }
$frontendPort = if ($env:FRONTEND_PORT) { $env:FRONTEND_PORT } else { "3000" }

if (-not $SkipBackend) {
    $apiArgs = @("-m", "uvicorn", "src.main:app", "--reload", "--port", $apiPort)
    $apiParams = @{
        FilePath = $backendPython
        ArgumentList = $apiArgs
        WorkingDirectory = $backendDir
        PassThru = $true
    }
    if (-not $Detach) {
        $apiParams.NoNewWindow = $true
    }
    $processes += Start-Process @apiParams
}

if (-not $SkipWebsocket) {
    $wsArgs = @("-m", "uvicorn", "src.websocket_server:app", "--reload", "--port", $wsPort)
    $wsParams = @{
        FilePath = $backendPython
        ArgumentList = $wsArgs
        WorkingDirectory = $backendDir
        PassThru = $true
    }
    if (-not $Detach) {
        $wsParams.NoNewWindow = $true
    }
    $processes += Start-Process @wsParams
}

if (-not $SkipFrontend) {
    $feParams = @{
        FilePath = "pnpm"
        ArgumentList = @("dev", "--", "--port", $frontendPort)
        WorkingDirectory = $frontendDir
        PassThru = $true
    }
    if (-not $Detach) {
        $feParams.NoNewWindow = $true
    }
    $processes += Start-Process @feParams
}

if ($processes.Count -eq 0) {
    Write-Error "Nothing to run. Remove one or more skip flags."
}

Write-Host "Services running:" -ForegroundColor Cyan
Write-Host (" - API: http://localhost:{0}" -f $apiPort)
Write-Host (" - WebSocket: http://localhost:{0}/ws" -f $wsPort)
Write-Host (" - Frontend: http://localhost:{0}" -f $frontendPort)
Write-Host ("PIDs: {0}" -f ($processes | ForEach-Object { $_.Id } | Sort-Object))

if ($Detach) {
    Write-Host "Detach mode enabled; processes are running in the background." -ForegroundColor Yellow
    return
}

try {
    Wait-Process -Id $processes.Id
} finally {
    Stop-Process -Id $processes.Id -Force -ErrorAction SilentlyContinue
}
