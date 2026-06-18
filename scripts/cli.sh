#!/usr/bin/env bash
# Interactive CLI, or one-shot if a question is passed as arguments.
#
# Usage:
#   scripts/cli.sh                       # interactive REPL
#   scripts/cli.sh "SceneMgr 是做什么的？"  # one-shot
#   scripts/cli.sh --repo ecs "MoveSystem 是做什么的？"
#   TARGET_CODE_PATH=/path scripts/cli.sh  # single-repo compatibility
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_venv
run_py -m code_agent.cli "$@"
