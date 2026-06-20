#!/usr/bin/env bash
# MCP server (streamable-http) exposing ask_codebase to MCP clients.
#
# Env (see code_agent.config / code_agent.interfaces.mcp_server): MCP_HOST, MCP_PORT (8901), MCP_PATH (/mcp),
# plus the usual AGENT_BACKEND / CODE_REPOS / CODE_REPO_DEFAULT / LLM_API_KEY.
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
daemon_dispatch mcp "${1:-}" -m code_agent.interfaces.mcp_server
