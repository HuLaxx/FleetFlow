#!/usr/bin/env bash
set -euo pipefail

SKIP_UP=false
SKIP_TESTS=false
SKIP_FRONTEND=false
SKIP_DATA=false
SKIP_ML=false
SKIP_ML_TRAINING=false

for arg in "$@"; do
  case "$arg" in
    --skip-up) SKIP_UP=true ;;
    --skip-tests) SKIP_TESTS=true ;;
    --skip-frontend) SKIP_FRONTEND=true ;;
    --skip-data) SKIP_DATA=true ;;
    --skip-ml) SKIP_ML=true ;;
    --skip-ml-training) SKIP_ML_TRAINING=true ;;
  esac
 done

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Required command not found: $1"; exit 1; }
}

require_cmd docker

if [ "$SKIP_FRONTEND" = false ]; then
  require_cmd node
  require_cmd pnpm
fi

"$(dirname "$0")/load-ports.sh"
API_PORT="${API_PORT:-8000}"
WS_PORT="${WS_PORT:-8002}"
KAFKA_UI_PORT="${KAFKA_UI_PORT:-8080}"
AIRFLOW_PORT="${AIRFLOW_PORT:-8081}"
FLINK_PORT="${FLINK_PORT:-8082}"
MLFLOW_PORT="${MLFLOW_PORT:-5001}"
OSRM_PORT="${OSRM_PORT:-5000}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ "$SKIP_ML" = false ] || [ "$SKIP_ML_TRAINING" = false ]; then
  require_cmd python
fi

if [ "$SKIP_UP" = false ]; then
  "$(dirname "$0")/dev-up.sh"
fi

check_endpoint() {
  local name="$1"
  local url="$2"
  if curl -fsS "$url" >/dev/null; then
    echo "OK  $name"
  else
    echo "FAIL $name ($url)"
    exit 1
  fi
}

check_endpoint "API" "http://localhost:${API_PORT}/health"
check_endpoint "WebSocket" "http://localhost:${WS_PORT}/health"
check_endpoint "Kafka UI" "http://localhost:${KAFKA_UI_PORT}"
check_endpoint "Airflow" "http://localhost:${AIRFLOW_PORT}"
check_endpoint "Flink" "http://localhost:${FLINK_PORT}"
check_endpoint "MLflow" "http://localhost:${MLFLOW_PORT}"
check_endpoint "OSRM" "http://localhost:${OSRM_PORT}"

if [ "$SKIP_DATA" = false ]; then
  "$(dirname "$0")/seed-db.sh" --reset
  "$(dirname "$0")/replay-kafka.sh"
fi

if [ "$SKIP_TESTS" = false ]; then
  BACKEND_PYTHON="$("$ROOT/scripts/backend-python.sh" --ensure-deps)"
  pushd "$(dirname "$0")/../backend" >/dev/null
  "$BACKEND_PYTHON" -m pytest --cov=src --cov-report=term-missing --cov-fail-under=85
  "$BACKEND_PYTHON" -m ruff check src
  "$BACKEND_PYTHON" -m black --check src
  "$BACKEND_PYTHON" -m mypy src
  popd >/dev/null

  if [ "$SKIP_ML" = false ]; then
    pushd "$(dirname "$0")/../ml" >/dev/null
    python -m pytest -m "not slow"
    popd >/dev/null
  fi

  if [ "$SKIP_FRONTEND" = false ]; then
    pushd "$(dirname "$0")/../frontend" >/dev/null
    pnpm lint
    pnpm test:e2e
    popd >/dev/null
  fi
fi

if [ "$SKIP_ML_TRAINING" = false ]; then
  "$(dirname "$0")/train-forecast.sh"
fi

echo "Local readiness validation complete."
