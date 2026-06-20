#!/usr/bin/env bash
# Build (or incrementally update) the offline symbol index (方案 2).
#
# Env: TARGET_CODE_PATH (single repo), or CODE_REPOS/CODE_REPO_DEFAULT (multi repo).
#
# Usage:
#   scripts/index.sh                 # full rebuild
#   scripts/index.sh --update        # incremental: only re-index changed files
#   scripts/index.sh --repo ecs      # build the ecs repo index from CODE_REPOS
#   TARGET_CODE_PATH=/path/to/code scripts/index.sh
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_venv
echo "[index] repos  : ${CODE_REPOS:-<single ${TARGET_CODE_PATH:-./target_code}>}"
echo "[index] default: ${CODE_REPO_DEFAULT:-<default>}"
echo "[index] db     : ${INDEX_DB_PATH:-<repo-specific default>}"
run_py -m code_agent.retrieval.indexer "$@"
