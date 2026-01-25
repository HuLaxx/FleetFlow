#!/usr/bin/env bash
set -euo pipefail

PBF_URL=${OSRM_PBF_URL:-"https://download.geofabrik.de/north-america/us-northeast-latest.osm.pbf"}
PBF_FILE=$(basename "$PBF_URL")
DATASET=${OSRM_DATASET:-"${PBF_FILE%.osm.pbf}.osrm"}

echo "Preparing OSRM data..."
echo "PBF URL: $PBF_URL"
echo "PBF File: $PBF_FILE"
echo "OSRM Dataset: $DATASET"

docker volume create osrm_data >/dev/null

docker run --rm -v osrm_data:/data alpine:3.19 sh -c "apk add --no-cache curl > /dev/null && curl -L -o /data/$PBF_FILE $PBF_URL"

docker run --rm -v osrm_data:/data osrm/osrm-backend osrm-extract -p /opt/car.lua /data/$PBF_FILE

docker run --rm -v osrm_data:/data osrm/osrm-backend osrm-partition /data/$DATASET

docker run --rm -v osrm_data:/data osrm/osrm-backend osrm-customize /data/$DATASET

echo "OSRM data prepared in Docker volume 'osrm_data'."