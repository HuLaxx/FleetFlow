#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/.env.ports"

if [[ ! -f "$ENV_FILE" ]]; then
  "$ROOT/scripts/ports-auto.sh"
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
