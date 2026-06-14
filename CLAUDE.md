# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Implemented and verified end-to-end (方案 1): `config.py`, `tools.py`, `agent.py`, `main.py`, `cli.py`, `requirements.txt`. A sample `target_code/` tree exists for local testing. No automated test suite yet.

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

The agent is a **tool-calling loop**: the LLM is given four code-search tools and iterates (call tool → feed result back → repeat) until it can answer. Tools to implement in `tools.py`:

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
| `main.py` | FastAPI service (`POST /ask`, `GET /health`), runs on port **8900** |
| `cli.py` | Interactive command-line testing mode |

## Commands

Prefer the wrappers in `scripts/` — they resolve the project root from their own
location (runnable from any CWD) and auto-create the venv on first use:

```bash
scripts/setup.sh                          # create venv + install deps
scripts/serve.sh                          # run HTTP service (port 8900)
scripts/cli.sh ["question"]               # interactive REPL, or one-shot if arg given
scripts/ask.sh [--no-cache] "question"    # curl a RUNNING service's POST /ask
```

`scripts/common.sh` is a sourced helper (PROJECT_ROOT, VENV_PY, `ensure_venv`,
`run_py`), not run directly. Equivalent raw commands:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
.venv/bin/python cli.py ["question"]
```

Use a venv — the system Python is PEP 668 externally-managed and rejects `pip install`. No test, lint, or build tooling is defined yet; the tools layer is pure-Python and testable without the LLM (import `tools` and call directly).

## Configuration

Set via env vars (or edit `config.py`):

| Var | Default |
|-----|---------|
| `LLM_MODEL` | `vertex_ai/gemini-3.5-flash` |
| `LLM_API_BASE` | `https://mushigen.comet.scopelyai.com/v1` |
| `LLM_API_KEY` | (provided in README) |
| `TARGET_CODE_PATH` | `./target_code` |

LLM access goes through **litellm** to the mushigen proxy — do not call the model provider SDK directly.

**Proxy routing gotcha:** mushigen is an OpenAI-compatible gateway at `/v1`. litellm picks its client from the model's leading provider segment, so a bare `vertex_ai/…` model triggers litellm's *native* Google Cloud auth (fails with `ModuleNotFoundError: google` / "Google Cloud SDK not found") and never reaches the proxy. `agent.py` therefore prepends `openai/` to `LLM_MODEL` (`_routed_model()`), forcing the OpenAI-compatible path; the proxy still receives the real model name after the prefix. Keep this prefixing if you touch the LLM call.

## API

`POST /ask` — body `{"question": str, "use_cache": bool}` → `{"answer": str, "cached": bool}`.
`GET /health` → `{"status": "ok"}`.

`use_cache`/`cached` imply a caching layer for repeated questions — implement this in or behind `main.py`.

## Roadmap (informs design decisions)

1. **Now (方案 1):** LLM + live code search, every query goes through tool calls.
2. **Next (方案 2):** offline indexing (tree-sitter AST → SQLite symbol table + vector DB) so exact queries can return without invoking the LLM.

Keep the tool layer separable so the future index can back the same tools.
