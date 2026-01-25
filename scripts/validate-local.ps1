param(
    [switch]$SkipUp,
    [switch]$SkipTests,
    [switch]$SkipFrontend,
    [switch]$SkipData,
    [switch]$SkipMl,
    [switch]$SkipMlTraining
)

$ErrorActionPreference = 'Stop'

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Write-Error "Required command not found: $Name"
    }
}

Require-Command docker

if (-not $SkipFrontend) {
    Require-Command node
    Require-Command pnpm
}

. "$PSScriptRoot\load-ports.ps1"

if (-not $SkipMl -or -not $SkipMlTraining) {
    Require-Command python
}

if (-not $SkipUp) {
    & "$PSScriptRoot\dev-up.ps1"
}

$apiPort = if ($env:API_PORT) { $env:API_PORT } else { "8000" }
$wsPort = if ($env:WS_PORT) { $env:WS_PORT } else { "8002" }
$kafkaUiPort = if ($env:KAFKA_UI_PORT) { $env:KAFKA_UI_PORT } else { "8080" }
$airflowPort = if ($env:AIRFLOW_PORT) { $env:AIRFLOW_PORT } else { "8081" }
$flinkPort = if ($env:FLINK_PORT) { $env:FLINK_PORT } else { "8082" }
$mlflowPort = if ($env:MLFLOW_PORT) { $env:MLFLOW_PORT } else { "5001" }
$osrmPort = if ($env:OSRM_PORT) { $env:OSRM_PORT } else { "5000" }

$endpoints = @(
    @{ Name = 'API'; Url = "http://localhost:$apiPort/health" },
    @{ Name = 'WebSocket'; Url = "http://localhost:$wsPort/health" },
    @{ Name = 'Kafka UI'; Url = "http://localhost:$kafkaUiPort" },
    @{ Name = 'Airflow'; Url = "http://localhost:$airflowPort" },
    @{ Name = 'Flink'; Url = "http://localhost:$flinkPort" },
    @{ Name = 'MLflow'; Url = "http://localhost:$mlflowPort" },
    @{ Name = 'OSRM'; Url = "http://localhost:$osrmPort" }
)

foreach ($endpoint in $endpoints) {
    try {
        Invoke-WebRequest -UseBasicParsing -Uri $endpoint.Url -TimeoutSec 5 | Out-Null
        Write-Host "OK  $($endpoint.Name)" -ForegroundColor Green
    } catch {
        Write-Error "FAIL $($endpoint.Name) at $($endpoint.Url)"
    }
}

if (-not $SkipData) {
    & "$PSScriptRoot\seed-db.ps1" --reset
    & "$PSScriptRoot\replay-kafka.ps1"
}

if (-not $SkipTests) {
    $backendPython = & "$PSScriptRoot\backend-python.ps1" -EnsureDeps
    Push-Location "$PSScriptRoot\..\backend"
    & $backendPython -m pytest --cov=src --cov-report=term-missing --cov-fail-under=85
    & $backendPython -m ruff check src
    & $backendPython -m black --check src
    & $backendPython -m mypy src
    Pop-Location

    if (-not $SkipMl) {
        Push-Location "$PSScriptRoot\..\ml"
        python -m pytest -m "not slow"
        Pop-Location
    }

    if (-not $SkipFrontend) {
        Push-Location "$PSScriptRoot\..\frontend"
        pnpm lint
        pnpm test:e2e
        Pop-Location
    }
}

if (-not $SkipMlTraining) {
    & "$PSScriptRoot\train-forecast.ps1"
}

Write-Host "Local readiness validation complete." -ForegroundColor Cyan
