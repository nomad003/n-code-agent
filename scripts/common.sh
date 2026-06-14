#!/usr/bin/env bash
# Shared helpers sourced by the other scripts. Not meant to be run directly.
set -euo pipefail

# Project root = parent of this scripts/ directory, resolved no matter the CWD.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"
VENV_PY="$VENV_DIR/bin/python"

# Auto-load .env (e.g. LLM_API_KEY) if present. Existing env vars win, since we
# only set names that aren't already exported.
if [[ -f "$PROJECT_ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$PROJECT_ROOT/.env"
  set +a
fi

# Ensure the venv exists and deps are installed; create on first use.
ensure_venv() {
  if [[ ! -x "$VENV_PY" ]]; then
    echo "[setup] .venv not found — creating it..."
    "$PROJECT_ROOT/scripts/setup.sh"
  fi
}

# Run the project's python with PROJECT_ROOT as CWD so relative paths resolve.
run_py() {
  cd "$PROJECT_ROOT"
  exec "$VENV_PY" "$@"
}
