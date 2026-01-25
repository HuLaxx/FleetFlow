param(
    [switch]$EnsureDeps
)

$ErrorActionPreference = 'Stop'

$backendDir = (Resolve-Path "$PSScriptRoot\..\backend").Path
$venvDir = Join-Path $backendDir ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

function Get-Python311Command {
    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCmd) {
        $versionCheck = & $pyCmd.Source -3.11 -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)"
        if ($LASTEXITCODE -eq 0) {
            return @{ Command = $pyCmd.Source; Args = @("-3.11") }
        }
    }

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        & $pythonCmd.Source -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)"
        if ($LASTEXITCODE -eq 0) {
            return @{ Command = $pythonCmd.Source; Args = @() }
        }
    }

    Write-Error "Python 3.11+ not found. Install Python 3.11 and retry."
}

if (-not (Test-Path $venvPython)) {
    $pythonCmd = Get-Python311Command
    Write-Host "Creating backend venv with Python 3.11..."
    $pythonArgs = $pythonCmd.Args
    & $pythonCmd.Command @pythonArgs -m venv $venvDir
    if (-not (Test-Path $venvPython)) {
        Write-Error "Failed to create backend venv at $venvDir"
    }
}

if ($EnsureDeps) {
    Push-Location $backendDir
    try {
        $previousErrorAction = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            & $venvPython -c "import confluent_kafka" 2>$null | Out-Null
            $importOk = ($LASTEXITCODE -eq 0)
        } finally {
            $ErrorActionPreference = $previousErrorAction
        }
        if (-not $importOk) {
            Write-Host "Installing backend dependencies..."
            & $venvPython -m pip install -U pip
            & $venvPython -m pip install -e ".[dev]"
        }
    } finally {
        Pop-Location
    }
}

Write-Output $venvPython
