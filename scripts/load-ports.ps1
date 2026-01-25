param(
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$root = (Resolve-Path "$PSScriptRoot\..").Path
$envFile = Join-Path $root ".env.ports"

if (-not (Test-Path $envFile)) {
    $argsList = @()
    if ($Force) {
        $argsList += "-Force"
    }
    & "$PSScriptRoot\ports-auto.ps1" @argsList
}

Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) {
        return
    }
    $parts = $line -split "=", 2
    if ($parts.Count -eq 2) {
        $name = $parts[0].Trim()
        $value = $parts[1].Trim()
        if ($name) {
            Set-Item -Path "Env:$name" -Value $value
        }
    }
}
