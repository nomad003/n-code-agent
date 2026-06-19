#!/usr/bin/env bash
# Run the offline code-knowledge evaluation.
#
# This checks versioned markdown cards under docs/code-knowledge/ directly:
# recall hit-rate, expected frontmatter/body fields, graph relation integrity,
# and broken knowledge links. It does not call the LLM.
#
# Usage:
#   scripts/knowledge-eval.sh
#   scripts/knowledge-eval.sh eval/knowledge.marvel.jsonl --top-k 5
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_venv
dataset="${1:-eval/knowledge.marvel.jsonl}"
shift || true
run_py -m code_agent.knowledge_eval "$dataset" "$@"
