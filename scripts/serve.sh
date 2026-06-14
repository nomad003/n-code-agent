#!/usr/bin/env bash
# FastAPI HTTP service (default port 8900).
#
# Optional env vars (see config.py): TARGET_CODE_PATH, SERVICE_PORT,
# SERVICE_HOST, LLM_MODEL, AGENT_MAX_ITERATIONS.
#
# Usage:
#   scripts/serve.sh                 # run in foreground (Ctrl-C to stop)
#   scripts/serve.sh start           # start in background
#   scripts/serve.sh stop            # stop the background service
#   scripts/serve.sh restart|status
#   TARGET_CODE_PATH=/path scripts/serve.sh start
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

if [[ -z "${1:-}" ]]; then
  ensure_venv
  echo "[serve] target code : ${TARGET_CODE_PATH:-<default ./target_code>}"
  echo "[serve] port        : ${SERVICE_PORT:-8900}"
fi
daemon_dispatch serve main.py "${1:-}"
