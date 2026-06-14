#!/usr/bin/env bash
# Start the MCP server (streamable-http) exposing ask_codebase to MCP clients.
#
# Env (see config.py / mcp_server.py): MCP_HOST, MCP_PORT (8901), MCP_PATH (/mcp),
# plus the usual AGENT_BACKEND / TARGET_CODE_PATH / LLM_API_KEY.
#
# Usage:
#   scripts/mcp.sh
#   MCP_PORT=8901 AGENT_BACKEND=sdk scripts/mcp.sh
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_venv
echo "[mcp] backend : ${AGENT_BACKEND:-custom}"
echo "[mcp] endpoint: http://${MCP_HOST:-0.0.0.0}:${MCP_PORT:-8901}${MCP_PATH:-/mcp}"
run_py mcp_server.py
