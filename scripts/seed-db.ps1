param(
    [switch]$Reset
)

$ErrorActionPreference = 'Stop'
$resetFlag = $Reset.IsPresent ? "--reset" : ""
. "$PSScriptRoot\load-ports.ps1"
$backendPython = & "$PSScriptRoot\backend-python.ps1" -EnsureDeps
& $backendPython "${PSScriptRoot}\..\backend\scripts\seed_db.py" $resetFlag
