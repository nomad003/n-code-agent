#!/usr/bin/env bash
# Start the FastAPI HTTP service (default port 8900).
#
# Optional env vars (see config.py): TARGET_CODE_PATH, SERVICE_PORT,
# SERVICE_HOST, LLM_MODEL, AGENT_MAX_ITERATIONS.
#
# Usage:
#   scripts/serve.sh
#   TARGET_CODE_PATH=/path/to/game-code scripts/serve.sh
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_venv
echo "[serve] target code : ${TARGET_CODE_PATH:-<default ./target_code>}"
echo "[serve] port        : ${SERVICE_PORT:-8900}"
run_py main.py
