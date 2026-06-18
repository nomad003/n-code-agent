# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Implemented and verified end-to-end: 方案 1 (litellm/SDK tool-calling loop) + 方案 2 first step (offline tree-sitter C++ symbol index). Entrypoints: `code_agent.main` (REST), `code_agent.mcp_server` (MCP), `code_agent.cli`. Offline pytest suite under `tests/`.

Detailed docs live in `docs/` ([architecture](docs/architecture.md), [configuration](docs/configuration.md), [api](docs/api.md), [deployment](docs/deployment.md)) — keep them in sync when changing behavior.

## What this is

A "游戏服务器/战斗/客户端/引擎 代码理解服务" (code-comprehension service): an HTTP API that answers natural-language questions about a separate game codebase — spanning the game server, combat, client, and engine modules — explaining its structure, field meanings, and feature flows. It does this by giving an LLM tool-call access to grep/read/list over the target code.

## Architecture

Request flow:

```
HTTP POST /ask  →  FastAPI (code_agent.main)  →  LLM agent loop (code_agent.agent)
                                              │  litellm
                                              ▼
                                   mushigen proxy → gemini-3.5-flash
```

### Two interchangeable backends

`agent.answer()` dispatches on the `AGENT_BACKEND` env var:

- **`custom`** (default) — the litellm tool-calling loop in `code_agent.agent` (`CodeAgent`). Provider-agnostic; routes through the `/v1` proxy with the `openai/` prefix. Model = `LLM_MODEL`. Keeps an `Action`/`Observation` event history (`code_agent.events`), builds messages in one place (`_build_messages`), retries transient LLM errors (`LLM_NUM_RETRIES`), stops early on repeated identical tool calls (`STUCK_REPEAT_THRESHOLD`), and masks all but the most recent `OBS_KEEP_FULL` tool outputs to bound context.
- **`sdk`** — the Claude Agent SDK loop in `agent_sdk.py` (imported lazily). Uses `claude-agent-sdk` + the Claude Code CLI, routed to **Bedrock** via env vars (`CLAUDE_CODE_USE_BEDROCK`, `ANTHROPIC_BEDROCK_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, …). Model = `SDK_MODEL` (falls back to `ANTHROPIC_MODEL`).

**Both backends share the same `code_agent.tools` and `config.system_prompt_for_mode()`.** The SDK backend wraps the existing sandboxed tools as `@tool`/SDK-MCP tools that delegate to `tools.dispatch()` — so the path sandbox and output caps are identical — and disables the SDK's built-in Read/Grep/Glob/Bash/Write/Edit so the model is confined to our tools. `max_turns = MAX_ITERATIONS`.

The agent is a **tool-calling loop**: the LLM is given sandboxed repo tools and iterates (call tool → feed result back → repeat) until it can answer. Tools in `code_agent.tools`:

- `grep_code(pattern, path, output_mode, context, head_limit)` — search code for symbols/keywords
- `read_file(path, start, end)` — read a file slice
- `list_dir(path)` — list a directory
- `glob(pattern, path, head_limit)` — enumerate files by path pattern
- `find_symbol(name)` — locate a class/function definition
- `repo_overview()` — read the cached repo navigation/profile
- `resolve_frame(frame)` — map a backtrace frame to its definition (方向 F; class-aware narrowing)
- `find_log_source(message)` — reverse-lookup the code that prints a runtime log line (方向 F; value/prefix normalization → FTS)
- `recall_knowledge(query)` — recall past Q&A leads (方案 3; only advertised when `USE_KNOWLEDGE=1`)

Intended module responsibilities:

| File | Responsibility |
|------|----------------|
| `code_agent/config.py` | Model id, API base/key, repo config, system prompt |
| `code_agent/tools.py` | Search-tool implementations + schemas (index-backed, fall back to live scan) |
| `code_agent/indexer.py` | Build/`update()` the offline index (tree-sitter C++ → SQLite symbols + FTS5; incremental by file hash) |
| `code_agent/index_query.py` | Read-only index queries (returns None when no index → tools fall back) |
| `code_agent/shortcut.py` | Entry short-circuit: answer "where is X defined" from the index, skipping the LLM (方案 2) |
| `code_agent/diagnose.py` | Runtime diagnosis (方向 F): parse backtrace, map frames to code via index, run agent |
| `code_agent/knowledge.py` | Knowledge flywheel (方案 3): precipitate Q&A → SQLite/FTS, recall with staleness check |
| `code_agent/evaluate.py` | Eval harness (方向 E): score {question → expected files/symbols} dataset; `--twice` measures flywheel recall |
| `code_agent/agent.py` | Backend dispatch + custom loop (`CodeAgent`: event history, stuck detection, retries) |
| `code_agent/events.py` | `Action`/`Observation` event model for the custom loop |
| `code_agent/agent_sdk.py` | Claude Agent SDK backend (used when `AGENT_BACKEND=sdk`) |
| `code_agent/operation_modes.py` | Mode policy: plain/technical/edit, alias normalization, per-mode prompt rules |
| `code_agent/response_policy.py` | Output guardrail: strips code/config/command samples from plain-mode answers (idempotent, CJK lines preserved as prose) |
| `code_agent/llm_trace.py` | Per-request JSONL trace under `logs/llm/` (best-effort; never breaks the request) |
| `code_agent/trace_viewer.py` | Read-only helpers behind `/admin/llm-traces` (list + parse trace files with path-escape guard) |
| `code_agent/main.py` | FastAPI service (`POST /ask`, `POST /diagnose`, `GET /repos`, `GET /health`, `/admin/llm-traces`), runs on port **8900** |
| `code_agent/mcp_server.py` | MCP server exposing `ask_codebase` / `diagnose_crash` over streamable-http, port **8901** |
| `code_agent/cli.py` | Interactive command-line testing mode |
| `code_agent/repo_profile.py` | Per-repo navigation/profile cache builder and formatter |
| `vendor/claude-cli/` | Vendored Claude Code CLI (linux-x64) for the SDK backend; native binary stored via **Git LFS** |

`code_agent.main`, `code_agent.mcp_server`, and `code_agent.cli` are three entrypoints over the same `agent.answer(..., repo=...)`. The MCP server (`code_agent.mcp_server`) is a thin FastMCP adapter — high-level tools `ask_codebase(question, mode="", repo="")` and `diagnose_crash(..., repo="")` — run as its own process/port; start with `scripts/mcp.sh`. See [docs/mcp.md](docs/mcp.md).

### Operation modes & output policy

Every answer flows through two layers: the **mode** chosen by the request (`plain` / `technical` / `edit`) shapes the system prompt via `operation_modes.prompt()`, and `response_policy.enforce()` runs at the service boundary as a deterministic guardrail (mode-aware: in **plain** it strips fenced blocks, shell commands, JSON/YAML config samples, and code-shaped lines; in **technical**/**edit** it's a no-op). Lines containing any CJK character are treated as prose and preserved, so structured field descriptions like `- host: 主机地址` survive. `enforce()` is idempotent, safe to apply on the cache path. `/diagnose` is technical by definition and applies `enforce(..., mode="technical")` so frame/file:line references aren't stripped.

The mode policy is centralized — the request asks for a mode, but `AGENT_ALLOWED_MODES` must enable it; unknown name → **400**, disabled mode → **403**. The `/ask` answer cache keys on `(repo, mode, question)` so different repos and modes don't collide.

### LLM tracing

`llm_trace.LLMTrace` writes one JSONL file per request under `LLM_TRACE_DIR` (default `logs/llm/`). Events include `request_start`, `llm_request`/`llm_response` (one pair per round, with full message list), `tool_result`, `cache_hit`/`shortcut`, `llm_error`/`request_error`, and `request_end`. Logging is best-effort: any failure is swallowed so it can never break a user request. The SDK backend emits parallel `sdk_request`/`sdk_tool_use`/`sdk_text`/`sdk_result` events. Inspect traces via `GET /admin/llm-traces` (HTML viewer) or its JSON API; `trace_viewer._resolve_trace_file` guards against path-escape.

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
.venv/bin/python -m code_agent.main
.venv/bin/python -m code_agent.cli ["question"]
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
| `TARGET_CODE_PATH` | `./target_code` single-repo compatibility |
| `CODE_REPOS` | unset; e.g. `gameserver=/path/a,ecs=/path/b` |
| `CODE_REPO_DEFAULT` | `default` or first `CODE_REPOS` entry |

LLM access goes through **litellm** to the mushigen proxy — do not call the model provider SDK directly.

**Proxy routing gotcha:** the proxy is an OpenAI-compatible gateway at `/v1` (custom backend) and Bedrock at `/bedrock` (sdk backend); both default to `http://10.253.17.63:8090`. litellm picks its client from the model's leading provider segment, so a bare `vertex_ai/…` model triggers litellm's *native* Google Cloud auth (fails with `ModuleNotFoundError: google` / "Google Cloud SDK not found") and never reaches the proxy. `code_agent.agent` therefore prepends `openai/` to `LLM_MODEL` (`_routed_model()`), forcing the OpenAI-compatible path; the proxy still receives the real model name after the prefix. Keep this prefixing if you touch the LLM call.

## API

`POST /ask` — body `{"question": str, "use_cache": bool, "mode": str, "repo": str}` → `{"answer": str, "cached": bool}`.
`POST /diagnose` — body `{"backtrace": str, "log": str, "plain": bool, "repo": str}` → `{"answer", "frames", "resolved", "total_frames", "plain"}` (方向 F).
`GET /repos` / `GET /repos/{repo}/overview` expose configured repos and cached repo profiles.
`GET /health` → `{"status": "ok"}`.

`/ask` and `/diagnose` are async and run the blocking agent loop through a concurrency gate (`main._run_governed`): a bounded `ThreadPoolExecutor` (`MAX_CONCURRENCY` workers) is the real gate — a 504-timed-out request can't kill its thread, but the thread keeps occupying a worker so the cap holds (slot freed only when the thread actually finishes, decrement marshalled to the loop). `_inflight` (running+queued) admits up to `MAX_CONCURRENCY + MAX_QUEUE`, else 503. The `/ask` answer cache is a bounded LRU (`CACHE_MAX_ENTRIES`); cache hits bypass the gate.

`use_cache`/`cached` imply a caching layer for repeated questions — implement this in or behind `code_agent.main`.

## Roadmap (informs design decisions)

1. **方案 1 (done):** LLM + live code search, every query goes through tool calls.
2. **方案 2 (symbol index landed):** `code_agent.indexer` builds (and incrementally `update()`s) a tree-sitter C++ → SQLite symbol table + FTS5 index; `find_symbol`/`grep_code` use it and fall back to live scan. Precise "where is X defined" questions short-circuit the LLM entirely (`code_agent.shortcut`, `USE_SHORTCUT`).
3. **方案 3 (knowledge flywheel landed, off by default):** `knowledge.py` precipitates each Q&A and recalls related leads (with staleness check) on later questions. Toggle `USE_KNOWLEDGE=1`. Semantic recall deferred to V3. See [docs/roadmap.md](docs/roadmap.md).

Keep the tool layer separable so the future index can back the same tools.
