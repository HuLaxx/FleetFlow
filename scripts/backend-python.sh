#!/usr/bin/env bash
set -euo pipefail

ENSURE_DEPS=0
for arg in "$@"; do
  case "$arg" in
    --ensure-deps) ENSURE_DEPS=1 ;;
  esac
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT/backend"
VENV_DIR="$BACKEND_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"

version_ok() {
  "$1" -c "import sys; exit(0 if sys.version_info >= (3,11) else 1)" >/dev/null 2>&1
}

pick_python() {
  if command -v python3.11 >/dev/null 2>&1 && version_ok python3.11; then
    echo "python3.11"
    return 0
  fi
  if command -v python3 >/dev/null 2>&1 && version_ok python3; then
    echo "python3"
    return 0
  fi
  if command -v python >/dev/null 2>&1 && version_ok python; then
    echo "python"
    return 0
  fi
  return 1
}

if [[ ! -x "$VENV_PYTHON" ]]; then
  PYTHON_CMD="$(pick_python || true)"
  if [[ -z "$PYTHON_CMD" ]]; then
    echo "Python 3.11+ not found. Install Python 3.11 and retry." >&2
    exit 1
  fi
  echo "Creating backend venv with Python 3.11..."
  "$PYTHON_CMD" -m venv "$VENV_DIR"
fi

if [[ $ENSURE_DEPS -eq 1 ]]; then
  if ! "$VENV_PYTHON" -c "import confluent_kafka" >/dev/null 2>&1; then
    echo "Installing backend dependencies..."
    (cd "$BACKEND_DIR" && "$VENV_PYTHON" -m pip install -U pip && "$VENV_PYTHON" -m pip install -e ".[dev]")
  fi
fi

echo "$VENV_PYTHON"
