#!/usr/bin/env bash
set -euo pipefail

SEED=${1:-42}
EPOCHS=${2:-1}
START_DATE=${3:-"2023-01-01"}
END_DATE=${4:-"2023-01-15"}

python "$(dirname "$0")/../ml/training/train_forecaster.py" \
  --seed "$SEED" \
  --epochs "$EPOCHS" \
  --start-date "$START_DATE" \
  --end-date "$END_DATE"