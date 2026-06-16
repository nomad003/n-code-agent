# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Implemented and verified end-to-end: 方案 1 (litellm/SDK tool-calling loop) + 方案 2 first step (offline tree-sitter C++ symbol index). Entrypoints: `main.py` (REST), `mcp_server.py` (MCP), `cli.py`. Offline pytest suite under `tests/`.

Detailed docs live in `docs/` ([architecture](docs/architecture.md), [configuration](docs/configuration.md), [api](docs/api.md), [deployment](docs/deployment.md)) — keep them in sync when changing behavior.

## What this is

A "游戏服务器/战斗/客户端/引擎 代码理解服务" (code-comprehension service): an HTTP API that answers natural-language questions about a separate game codebase — spanning the game server, combat, client, and engine modules — explaining its structure, field meanings, and feature flows. It does this by giving an LLM tool-call access to grep/read/list over the target code.

## Architecture

Request flow:

```
HTTP POST /ask  →  FastAPI (main.py)  →  LLM agent loop (agent.py)
                                              │  litellm
                                              ▼
                                   mushigen proxy → gemini-3.5-flash
```

### Two interchangeable backends

`agent.answer()` dispatches on the `AGENT_BACKEND` env var:

- **`custom`** (default) — the litellm tool-calling loop in `agent.py` (`CodeAgent`). Provider-agnostic; routes through the `/v1` proxy with the `openai/` prefix. Model = `LLM_MODEL`. Keeps an `Action`/`Observation` event history (`events.py`), builds messages in one place (`_build_messages`), retries transient LLM errors (`LLM_NUM_RETRIES`), stops early on repeated identical tool calls (`STUCK_REPEAT_THRESHOLD`), and masks all but the most recent `OBS_KEEP_FULL` tool outputs to bound context.
- **`sdk`** — the Claude Agent SDK loop in `agent_sdk.py` (imported lazily). Uses `claude-agent-sdk` + the Claude Code CLI, routed to **Bedrock** via env vars (`CLAUDE_CODE_USE_BEDROCK`, `ANTHROPIC_BEDROCK_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, …). Model = `SDK_MODEL` (falls back to `ANTHROPIC_MODEL`).

**Both backends share the same `tools.py` and `config.SYSTEM_PROMPT`.** The SDK backend wraps the existing sandboxed tools as `@tool`/SDK-MCP tools that delegate to `tools.dispatch()` — so the path sandbox and output caps are identical — and disables the SDK's built-in Read/Grep/Bash so the model is confined to our four tools. `max_turns = MAX_ITERATIONS`.

The agent is a **tool-calling loop**: the LLM is given four code-search tools and iterates (call tool → feed result back → repeat) until it can answer. Tools in `tools.py`:

- `grep_code(pattern, path)` — search code for symbols/keywords
- `read_file(path, start, end)` — read a file slice
- `list_dir(path)` — list a directory
- `find_symbol(name)` — locate a class/function definition
- `resolve_frame(frame)` — map a backtrace frame to its definition (方向 F; class-aware narrowing)
- `find_log_source(message)` — reverse-lookup the code that prints a runtime log line (方向 F; value/prefix normalization → FTS)
- `recall_knowledge(query)` — recall past Q&A leads (方案 3; only advertised when `USE_KNOWLEDGE=1`)

Intended module responsibilities:

| File | Responsibility |
|------|----------------|
| `config.py` | Model id, API base/key, target-code path, system prompt |
| `tools.py` | The four search-tool implementations + schemas (index-backed, fall back to live scan) |
| `indexer.py` | Build/`update()` the offline index (tree-sitter C++ → SQLite symbols + FTS5; incremental by file hash) |
| `index_query.py` | Read-only index queries (returns None when no index → tools fall back) |
| `shortcut.py` | Entry short-circuit: answer "where is X defined" from the index, skipping the LLM (方案 2) |
| `diagnose.py` | Runtime diagnosis (方向 F): parse backtrace, map frames to code via index, run agent |
| `knowledge.py` | Knowledge flywheel (方案 3): precipitate Q&A → SQLite/FTS, recall with staleness check |
| `evaluate.py` | Eval harness (方向 E): score {question → expected files/symbols} dataset; `--twice` measures flywheel recall |
| `agent.py` | Backend dispatch + custom loop (`CodeAgent`: event history, stuck detection, retries) |
| `events.py` | `Action`/`Observation` event model for the custom loop |
| `agent_sdk.py` | Claude Agent SDK backend (used when `AGENT_BACKEND=sdk`) |
| `main.py` | FastAPI service (`POST /ask`, `GET /health`), runs on port **8900** |
| `mcp_server.py` | MCP server exposing `ask_codebase` over streamable-http, port **8901** |
| `cli.py` | Interactive command-line testing mode |
| `vendor/claude-cli/` | Vendored Claude Code CLI (linux-x64) for the SDK backend; native binary stored via **Git LFS** |

`main.py`, `mcp_server.py`, and `cli.py` are three entrypoints over the same `agent.answer()`. The MCP server (`mcp_server.py`) is a thin FastMCP adapter — one high-level tool `ask_codebase(question)` — run as its own process/port; start with `scripts/mcp.sh`. See [docs/mcp.md](docs/mcp.md).

## Commands

Prefer the wrappers in `scripts/` — they resolve the project root from their own
location (runnable from any CWD) and auto-create the venv on first use:

```bash
scripts/setup.sh                          # create venv + install deps
scripts/index.sh [--update]               # build (or incrementally update) the symbol index (方案 2)
scripts/eval.sh [dataset.jsonl] [--twice] # run the Q&A eval harness (方向 E)
scripts/serve.sh [start|stop|restart|status]  # HTTP service (8900); no arg = foreground
scripts/mcp.sh   [start|stop|restart|status]  # MCP server (8901); no arg = foreground
scripts/cli.sh ["question"]               # interactive REPL, or one-shot if arg given
scripts/ask.sh [--no-cache] "question"    # curl a RUNNING service's POST /ask
```

`serve.sh`/`mcp.sh` background mode writes `logs/<name>.{pid,log}`; `daemon_*` helpers live in `common.sh`. `stop` is graceful (SIGTERM, then SIGKILL after 10s).

`scripts/common.sh` is a sourced helper (PROJECT_ROOT, VENV_PY, `ensure_venv`,
`run_py`), not run directly. Equivalent raw commands:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
.venv/bin/python cli.py ["question"]
```

Use a venv — the system Python is PEP 668 externally-managed and rejects `pip install`.

### Tests

```bash
scripts/test.sh              # all tests (auto-installs pytest/httpx)
scripts/test.sh -k grep      # filter; or pass a nodeid like tests/test_api.py::test_health
```

pytest suite under `tests/` is **fully offline** — the LLM is monkeypatched, tools run against a temp codebase (`target_code` fixture). Covers the tool sandbox/caps/dispatch, `_routed_model()` prefixing, backend dispatch, and the `/ask` cache + 502 error path. Dev deps in `requirements-dev.txt`, config in `pytest.ini`. See [docs/testing.md](docs/testing.md). When changing tool or API behavior, update these tests.

**Git LFS:** `vendor/claude-cli/.../claude` (~239M, linux-x64) is stored via Git LFS (see `.gitattributes`). Cloning requires `git lfs` installed, or that binary comes down as a pointer file. The vendored CLI is **linux-x64 only**; on other platforms reinstall `@anthropic-ai/claude-code` or rely on a system `claude` on PATH (`agent_sdk._resolve_cli_path()` falls back to it).

## Configuration

Set via env vars (or edit `config.py`):

| Var | Default |
|-----|---------|
| `LLM_MODEL` | `vertex_ai/gemini-3.5-flash` |
| `LLM_API_BASE` | `http://10.253.17.63:8090/v1` |
| `LLM_API_KEY` | (provided in README) |
| `TARGET_CODE_PATH` | `./target_code` |

LLM access goes through **litellm** to the mushigen proxy — do not call the model provider SDK directly.

**Proxy routing gotcha:** the proxy is an OpenAI-compatible gateway at `/v1` (custom backend) and Bedrock at `/bedrock` (sdk backend); both default to `http://10.253.17.63:8090`. litellm picks its client from the model's leading provider segment, so a bare `vertex_ai/…` model triggers litellm's *native* Google Cloud auth (fails with `ModuleNotFoundError: google` / "Google Cloud SDK not found") and never reaches the proxy. `agent.py` therefore prepends `openai/` to `LLM_MODEL` (`_routed_model()`), forcing the OpenAI-compatible path; the proxy still receives the real model name after the prefix. Keep this prefixing if you touch the LLM call.

## API

`POST /ask` — body `{"question": str, "use_cache": bool}` → `{"answer": str, "cached": bool}`.
`POST /diagnose` — body `{"backtrace": str, "log": str}` → `{"answer", "frames", "resolved", "total_frames"}` (方向 F).
`GET /health` → `{"status": "ok"}`.

`/ask` and `/diagnose` are async and run the blocking agent loop through a concurrency gate (`main._run_governed`): `MAX_CONCURRENCY` slots + `MAX_QUEUE` queue (overflow → 503) + `REQUEST_TIMEOUT` (→ 504). Cache hits bypass the gate.

`use_cache`/`cached` imply a caching layer for repeated questions — implement this in or behind `main.py`.

## Roadmap (informs design decisions)

1. **方案 1 (done):** LLM + live code search, every query goes through tool calls.
2. **方案 2 (symbol index landed):** `indexer.py` builds (and incrementally `update()`s) a tree-sitter C++ → SQLite symbol table + FTS5 index; `find_symbol`/`grep_code` use it and fall back to live scan. Precise "where is X defined" questions short-circuit the LLM entirely (`shortcut.py`, `USE_SHORTCUT`).
3. **方案 3 (knowledge flywheel landed, off by default):** `knowledge.py` precipitates each Q&A and recalls related leads (with staleness check) on later questions. Toggle `USE_KNOWLEDGE=1`. Semantic recall deferred to V3. See [docs/roadmap.md](docs/roadmap.md).

Keep the tool layer separable so the future index can back the same tools.
