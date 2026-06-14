#!/usr/bin/env bash
# Create the venv (if missing) and install dependencies.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "[setup] creating venv at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

echo "[setup] installing requirements"
"$VENV_DIR/bin/pip" install -q -r "$PROJECT_ROOT/requirements.txt"
echo "[setup] done"
