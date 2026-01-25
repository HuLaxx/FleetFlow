#!/usr/bin/env bash
set -euo pipefail

SKIP_INFRA=0
SKIP_BACKEND=0
SKIP_WEBSOCKET=0
SKIP_FRONTEND=0
DETACH=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-infra) SKIP_INFRA=1 ;;
    --skip-backend) SKIP_BACKEND=1 ;;
    --skip-websocket) SKIP_WEBSOCKET=1 ;;
    --skip-frontend) SKIP_FRONTEND=1 ;;
    --detach) DETACH=1 ;;
    *)
      echo "Unknown flag: $1"
      exit 1
      ;;
  esac
  shift
done

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command not found: $1"
    exit 1
  fi
}

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ $SKIP_INFRA -eq 0 ]]; then
  require_command docker
fi

if [[ $SKIP_FRONTEND -eq 0 ]]; then
  require_command node
  require_command pnpm
fi

"$ROOT/scripts/load-ports.sh"
API_PORT="${API_PORT:-8000}"
WS_PORT="${WS_PORT:-8002}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
BACKEND_PYTHON=""

if [[ $SKIP_BACKEND -eq 0 || $SKIP_WEBSOCKET -eq 0 ]]; then
  BACKEND_PYTHON="$("$ROOT/scripts/backend-python.sh" --ensure-deps)"
fi

if [[ $SKIP_INFRA -eq 0 ]]; then
  "$ROOT/scripts/dev-up.sh"
fi

pids=()

if [[ $SKIP_BACKEND -eq 0 ]]; then
  (cd "$ROOT/backend" && "$BACKEND_PYTHON" -m uvicorn src.main:app --reload --port "$API_PORT") &
  pids+=("$!")
fi

if [[ $SKIP_WEBSOCKET -eq 0 ]]; then
  (cd "$ROOT/backend" && "$BACKEND_PYTHON" -m uvicorn src.websocket_server:app --reload --port "$WS_PORT") &
  pids+=("$!")
fi

if [[ $SKIP_FRONTEND -eq 0 ]]; then
  (cd "$ROOT/frontend" && pnpm dev -- --port "$FRONTEND_PORT") &
  pids+=("$!")
fi

if [[ ${#pids[@]} -eq 0 ]]; then
  echo "Nothing to run. Remove one or more skip flags."
  exit 1
fi

echo "Services running:"
echo " - API: http://localhost:${API_PORT}"
echo " - WebSocket: http://localhost:${WS_PORT}/ws"
echo " - Frontend: http://localhost:${FRONTEND_PORT}"
echo "PIDs: ${pids[*]}"

if [[ $DETACH -eq 1 ]]; then
  echo "Detach mode enabled; processes are running in the background."
  for pid in "${pids[@]}"; do
    disown "$pid" 2>/dev/null || true
  done
  exit 0
fi

cleanup() {
  kill "${pids[@]}" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

wait
