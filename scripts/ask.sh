#!/usr/bin/env bash
# Ask a question against a RUNNING HTTP service (start it with scripts/serve.sh).
#
# Usage:
#   scripts/ask.sh "玩家的生命值字段叫什么？"
#   SERVICE_PORT=8900 scripts/ask.sh "..."        # override port
#   scripts/ask.sh --no-cache "..."               # bypass the cache
set -euo pipefail

host="${SERVICE_HOST:-localhost}"
port="${SERVICE_PORT:-8900}"
use_cache=true

if [[ "${1:-}" == "--no-cache" ]]; then
  use_cache=false
  shift
fi

if [[ $# -eq 0 ]]; then
  echo "usage: scripts/ask.sh [--no-cache] \"<question>\"" >&2
  exit 1
fi

question="$*"
# Build the JSON body safely (handles quotes/newlines in the question).
body=$(python3 -c 'import json,sys; print(json.dumps({"question": sys.argv[1], "use_cache": sys.argv[2]=="true"}))' "$question" "$use_cache")

curl -s -m 180 -X POST "http://${host}:${port}/ask" \
  -H "Content-Type: application/json" \
  -d "$body" | python3 -m json.tool --no-ensure-ascii
