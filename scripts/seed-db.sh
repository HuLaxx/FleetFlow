#!/usr/bin/env bash
set -euo pipefail

RESET_FLAG=""
if [[ "${1:-}" == "--reset" ]]; then
  RESET_FLAG="--reset"
fi

"$(dirname "$0")/load-ports.sh"

BACKEND_PYTHON="$("$(dirname "$0")/backend-python.sh" --ensure-deps)"
"$BACKEND_PYTHON" "$(dirname "$0")/../backend/scripts/seed_db.py" $RESET_FLAG
