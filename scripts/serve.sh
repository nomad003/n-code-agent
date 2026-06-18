#!/usr/bin/env bash
# FastAPI HTTP service (default port 8900).
#
# Optional env vars (see config.py): CODE_REPOS, CODE_REPO_DEFAULT,
# TARGET_CODE_PATH, SERVICE_PORT, SERVICE_HOST, LLM_MODEL, AGENT_MAX_ITERATIONS.
#
# Usage:
#   scripts/serve.sh                 # run in foreground (Ctrl-C to stop)
#   scripts/serve.sh start           # start in background
#   scripts/serve.sh stop            # stop the background service
#   scripts/serve.sh restart|status
#   CODE_REPOS='gameserver=/path/a,ecs=/path/b' scripts/serve.sh start
#   TARGET_CODE_PATH=/path scripts/serve.sh start  # single-repo compatibility
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

if [[ -z "${1:-}" ]]; then
  ensure_venv
  echo "[serve] repos       : ${CODE_REPOS:-<single ${TARGET_CODE_PATH:-./target_code}>}"
  echo "[serve] default repo: ${CODE_REPO_DEFAULT:-<default>}"
  echo "[serve] port        : ${SERVICE_PORT:-8900}"
fi
daemon_dispatch serve "${1:-}" -m code_agent.main
