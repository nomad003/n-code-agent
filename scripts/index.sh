#!/usr/bin/env bash
# Build (or incrementally update) the offline symbol index (方案 2).
#
# Env: TARGET_CODE_PATH (what to index), INDEX_DB_PATH (where to write).
#
# Usage:
#   scripts/index.sh                 # full rebuild
#   scripts/index.sh --update        # incremental: only re-index changed files
#   TARGET_CODE_PATH=/path/to/code scripts/index.sh
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_venv
echo "[index] target : ${TARGET_CODE_PATH:-<default ./target_code>}"
echo "[index] db     : ${INDEX_DB_PATH:-<default ./index/code_index.db>}"
run_py indexer.py "$@"
