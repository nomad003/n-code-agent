#!/usr/bin/env bash
# MCP server (streamable-http) exposing ask_codebase to MCP clients.
#
# Env (see config.py / mcp_server.py): MCP_HOST, MCP_PORT (8901), MCP_PATH (/mcp),
# plus the usual AGENT_BACKEND / TARGET_CODE_PATH / LLM_API_KEY.
#
# Usage:
#   scripts/mcp.sh                   # run in foreground (Ctrl-C to stop)
#   scripts/mcp.sh start             # start in background
#   scripts/mcp.sh stop              # stop the background server
#   scripts/mcp.sh restart|status
#   MCP_PORT=8901 scripts/mcp.sh start
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

if [[ -z "${1:-}" ]]; then
  ensure_venv
  echo "[mcp] backend : ${AGENT_BACKEND:-custom}"
  echo "[mcp] endpoint: http://${MCP_HOST:-0.0.0.0}:${MCP_PORT:-8901}${MCP_PATH:-/mcp}"
fi
daemon_dispatch mcp mcp_server.py "${1:-}"
