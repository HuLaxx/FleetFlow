param(
    [int]$Seed = 42
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\load-ports.ps1"
$backendPython = & "$PSScriptRoot\backend-python.ps1" -EnsureDeps
& $backendPython "${PSScriptRoot}\..\backend\scripts\replay_kafka.py" --seed $Seed
