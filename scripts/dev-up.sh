#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"$ROOT/scripts/ports-auto.sh"

echo "Starting FleetFlow local stack with profiles: data, ml, routing"
if ! docker compose -f "$ROOT/docker-compose.yml" --env-file "$ROOT/.env.ports" --profile data --profile ml --profile routing up -d; then
  echo "docker compose --profile failed; falling back to COMPOSE_PROFILES"
  COMPOSE_PROFILES="data,ml,routing" docker compose -f "$ROOT/docker-compose.yml" --env-file "$ROOT/.env.ports" up -d
fi
