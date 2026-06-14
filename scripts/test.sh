#!/usr/bin/env bash
# Install dev deps (if needed) and run the test suite. Offline — no LLM/network.
#
# Usage:
#   scripts/test.sh                 # run all tests
#   scripts/test.sh tests/test_tools.py::test_grep_finds_match   # run one
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_venv
# Ensure pytest is available without forcing a full reinstall every run.
if ! "$VENV_PY" -c 'import pytest' 2>/dev/null; then
  echo "[test] installing dev dependencies"
  "$VENV_DIR/bin/pip" install -q -r "$PROJECT_ROOT/requirements-dev.txt"
fi

cd "$PROJECT_ROOT"
exec "$VENV_PY" -m pytest "$@"
