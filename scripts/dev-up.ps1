# Start full local stack (data + ml + routing profiles)
$profiles = @("data", "ml", "routing")
$profileArgs = $profiles | ForEach-Object { "--profile=$_" }
$root = (Resolve-Path "$PSScriptRoot\..").Path
$composeFile = Join-Path $root "docker-compose.yml"
$envFile = Join-Path $root ".env.ports"

& "$PSScriptRoot\ports-auto.ps1"

Write-Host "Starting FleetFlow local stack with profiles: $($profiles -join ', ')"
docker compose -f $composeFile --env-file $envFile @profileArgs up -d
if ($LASTEXITCODE -ne 0) {
    Write-Warning "docker compose --profile failed; falling back to COMPOSE_PROFILES"
    $previousProfiles = $env:COMPOSE_PROFILES
    try {
        $env:COMPOSE_PROFILES = ($profiles -join ",")
        docker compose -f $composeFile --env-file $envFile up -d
        if ($LASTEXITCODE -ne 0) {
            throw "docker compose up failed (exit $LASTEXITCODE)"
        }
    } finally {
        if ($null -ne $previousProfiles) {
            $env:COMPOSE_PROFILES = $previousProfiles
        } else {
            Remove-Item Env:\COMPOSE_PROFILES -ErrorAction SilentlyContinue
        }
    }
}
