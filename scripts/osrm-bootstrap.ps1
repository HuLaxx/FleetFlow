param(
    [string]$PbfUrl = $env:OSRM_PBF_URL,
    [string]$Dataset = $env:OSRM_DATASET
)

if (-not $PbfUrl) {
    $PbfUrl = "https://download.geofabrik.de/north-america/us-northeast-latest.osm.pbf"
}

$PbfFile = Split-Path $PbfUrl -Leaf
if (-not $Dataset) {
    $Dataset = $PbfFile -replace "\.osm\.pbf$", ".osrm"
}

Write-Host "Preparing OSRM data..."
Write-Host "PBF URL: $PbfUrl"
Write-Host "PBF File: $PbfFile"
Write-Host "OSRM Dataset: $Dataset"

docker volume create osrm_data | Out-Null

docker run --rm -v osrm_data:/data alpine:3.19 sh -c "apk add --no-cache curl > /dev/null && curl -L -o /data/$PbfFile $PbfUrl"

docker run --rm -v osrm_data:/data osrm/osrm-backend osrm-extract -p /opt/car.lua /data/$PbfFile

docker run --rm -v osrm_data:/data osrm/osrm-backend osrm-partition /data/$Dataset

docker run --rm -v osrm_data:/data osrm/osrm-backend osrm-customize /data/$Dataset

Write-Host "OSRM data prepared in Docker volume 'osrm_data'."