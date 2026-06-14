# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Implemented and verified end-to-end (方案 1): `config.py`, `tools.py`, `agent.py`, `agent_sdk.py`, `main.py`, `cli.py`, `requirements.txt`. A sample `target_code/` tree exists for local testing. No automated test suite yet.

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

- **`custom`** (default) — the litellm tool-calling loop in `agent.py` (`_answer_custom`). Provider-agnostic; routes through the mushigen `/v1` proxy with the `openai/` prefix. Model = `LLM_MODEL`.
- **`sdk`** — the Claude Agent SDK loop in `agent_sdk.py` (imported lazily). Uses `claude-agent-sdk` + the Claude Code CLI, routed to **Bedrock** via env vars (`CLAUDE_CODE_USE_BEDROCK`, `ANTHROPIC_BEDROCK_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, …). Model = `SDK_MODEL` (falls back to `ANTHROPIC_MODEL`).

**Both backends share the same `tools.py` and `config.SYSTEM_PROMPT`.** The SDK backend wraps the existing sandboxed tools as `@tool`/SDK-MCP tools that delegate to `tools.dispatch()` — so the path sandbox and output caps are identical — and disables the SDK's built-in Read/Grep/Bash so the model is confined to our four tools. `max_turns = MAX_ITERATIONS`.

The agent is a **tool-calling loop**: the LLM is given four code-search tools and iterates (call tool → feed result back → repeat) until it can answer. Tools in `tools.py`:

- `grep_code(pattern, path)` — search code for symbols/keywords
- `read_file(path, start, end)` — read a file slice
- `list_dir(path)` — list a directory
- `find_symbol(name)` — locate a class/function definition

Intended module responsibilities:

| File | Responsibility |
|------|----------------|
| `config.py` | Model id, API base/key, target-code path, system prompt |
| `tools.py` | The four search-tool implementations + their tool-call schemas |
| `agent.py` | LLM interaction loop (tool calling) |
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
`GET /health` → `{"status": "ok"}`.

`use_cache`/`cached` imply a caching layer for repeated questions — implement this in or behind `main.py`.

## Roadmap (informs design decisions)

1. **Now (方案 1):** LLM + live code search, every query goes through tool calls.
2. **Next (方案 2):** offline indexing (tree-sitter AST → SQLite symbol table + vector DB) so exact queries can return without invoking the LLM.

Keep the tool layer separable so the future index can back the same tools.
