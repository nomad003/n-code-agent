#!/usr/bin/env bash
# Ask a question against a RUNNING HTTP service (start it with scripts/serve.sh).
#
# Usage:
#   scripts/ask.sh "玩家的生命值字段叫什么？"
#   SERVICE_PORT=8900 scripts/ask.sh "..."        # override port
#   scripts/ask.sh --no-cache "..."               # bypass the cache
#   scripts/ask.sh --mode technical "..."         # request an enabled mode
set -euo pipefail

host="${SERVICE_HOST:-localhost}"
port="${SERVICE_PORT:-8900}"
use_cache=true
mode=""

while [[ $# -gt 0 ]]; do
  case "${1:-}" in
    --no-cache)
      use_cache=false
      shift
      ;;
    --mode)
      if [[ $# -lt 2 ]]; then
        echo "usage: scripts/ask.sh [--no-cache] [--mode plain|technical|edit] \"<question>\"" >&2
        exit 1
      fi
      mode="$2"
      shift 2
      ;;
    *)
      break
      ;;
  esac
done

if [[ $# -eq 0 ]]; then
  echo "usage: scripts/ask.sh [--no-cache] [--mode plain|technical|edit] \"<question>\"" >&2
  exit 1
fi

question="$*"
# Build the JSON body safely (handles quotes/newlines in the question).
body=$(python3 -c 'import json,sys
body = {"question": sys.argv[1], "use_cache": sys.argv[2] == "true"}
if sys.argv[3]:
    body["mode"] = sys.argv[3]
print(json.dumps(body))' "$question" "$use_cache" "$mode")

curl -s -m 180 -X POST "http://${host}:${port}/ask" \
  -H "Content-Type: application/json" \
  -d "$body" | python3 -m json.tool --no-ensure-ascii
