#!/usr/bin/env bash
# Run the Q&A evaluation harness (方向 E + 方案 3 hit-rate).
#
# Usage:
#   scripts/eval.sh                      # run the sample dataset
#   scripts/eval.sh eval/my_set.jsonl    # a custom dataset
#   USE_KNOWLEDGE=1 scripts/eval.sh eval/my_set.jsonl --twice   # flywheel recall
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_venv
dataset="${1:-eval/dataset.sample.jsonl}"
shift || true

# The sample dataset targets the tiny repo-local fixture under target_code/scene.
# Keep it isolated from a developer's real CODE_REPOS/.env, otherwise the sample
# expectations are scored against gameserver and become meaningless.
case "$dataset" in
  eval/dataset.sample.jsonl|"$PROJECT_ROOT"/eval/dataset.sample.jsonl)
    export CODE_REPOS=
    export CODE_REPO_DEFAULT=default
    export TARGET_CODE_PATH="$PROJECT_ROOT/target_code"
    export USE_INDEX=0
    export CODE_KNOWLEDGE_MAP_ENABLED=0
    ;;
esac

run_py -m code_agent.evals.evaluate "$dataset" "$@"
