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
run_py -m code_agent.evaluate "$dataset" "$@"
