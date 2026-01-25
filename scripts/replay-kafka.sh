#!/usr/bin/env bash
set -euo pipefail

SEED=${1:-42}
"$(dirname "$0")/load-ports.sh"
BACKEND_PYTHON="$("$(dirname "$0")/backend-python.sh" --ensure-deps)"
"$BACKEND_PYTHON" "$(dirname "$0")/../backend/scripts/replay_kafka.py" --seed "$SEED"
