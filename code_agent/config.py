"""Global configuration for the code-comprehension service.

All values can be overridden by environment variables. LLM access always goes
through litellm to the mushigen proxy — never call a provider SDK directly.
"""
import contextlib
import contextvars
import os
from dataclasses import dataclass

from .core import operation_modes

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- LLM -------------------------------------------------------------------
LLM_MODEL = os.environ.get("LLM_MODEL", "vertex_ai/gemini-3.5-flash")
# The mushigen proxy is an OpenAI-compatible gateway. litellm must route every
# model through it as an "openai/" custom endpoint — otherwise a "vertex_ai/"
# prefix triggers litellm's native Google Cloud auth (which we don't use) and
# the request never hits the proxy.
LLM_API_BASE = os.environ.get("LLM_API_BASE", "http://10.253.17.63:8090/v1")
# No hardcoded default: the auth token must come from the environment (see
# .env.example). Keeps secrets out of the repo and git history.
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")

# --- Target codebase -------------------------------------------------------
# Absolute path to the target codebase (game server / combat / client / engine)
# that questions are asked about.
# Defaults to ./target_code under this repo so the service runs out of the box.
TARGET_CODE_PATH = os.path.abspath(
    os.environ.get(
        "TARGET_CODE_PATH",
        os.path.join(PROJECT_ROOT, "target_code"),
    )
)


@dataclass(frozen=True)
class CodeRepo:
    """One configured target code repository."""

    name: str
    path: str
    index_db_path: str
    knowledge_db_path: str
    profile_path: str


def _safe_repo_name(name: str) -> str:
    name = (name or "").strip()
    if not name:
        raise ValueError("repo name cannot be empty")
    if any(ch in name for ch in "/\\:"):
        raise ValueError(f"invalid repo name {name!r}: use letters, numbers, '-' or '_'")
    return name


def _repo_storage_path(repo_name: str, filename: str) -> str:
    return os.path.join(
        PROJECT_ROOT,
        "index",
        "repos",
        repo_name,
        filename,
    )


def _parse_code_repos(raw: str) -> dict[str, CodeRepo]:
    """Parse CODE_REPOS='gameserver=/path/a,ecs=/path/b'.

    The legacy TARGET_CODE_PATH remains the default when CODE_REPOS is unset.
    """
    repos: dict[str, CodeRepo] = {}
    for item in raw.replace(";", ",").split(","):
        item = item.strip()
        if not item:
            continue
        if "=" in item:
            name, path = item.split("=", 1)
        elif ":" in item:
            name, path = item.split(":", 1)
        else:
            raise ValueError(
                "CODE_REPOS entries must be 'name=/abs/path' or 'name:/abs/path'"
            )
        name = _safe_repo_name(name)
        path = os.path.abspath(os.path.expanduser(path.strip()))
        repos[name] = CodeRepo(
            name=name,
            path=path,
            index_db_path=_repo_storage_path(name, "code_index.db"),
            knowledge_db_path=_repo_storage_path(name, "knowledge.db"),
            profile_path=_repo_storage_path(name, "profile.json"),
        )
    return repos


_CODE_REPOS_RAW = os.environ.get("CODE_REPOS", "").strip()
CODE_REPOS = _parse_code_repos(_CODE_REPOS_RAW) if _CODE_REPOS_RAW else {}
CODE_REPO_DEFAULT = _safe_repo_name(
    os.environ.get("CODE_REPO_DEFAULT") or (next(iter(CODE_REPOS), "default"))
)
_CURRENT_REPO: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "code_agent_repo", default=None
)

# --- Agent backend ---------------------------------------------------------
# "custom" = the litellm tool-calling loop (default, model-agnostic via proxy).
# "sdk"    = the Claude Agent SDK loop (claude-agent-sdk + Claude Code CLI,
#            routed through Bedrock env vars). Both reuse the same sandboxed
#            tools in code_agent.retrieval.tools and expose the same agent.answer() interface.
AGENT_BACKEND = os.environ.get("AGENT_BACKEND", "custom").strip().lower()

# --- Operation/response mode ----------------------------------------------
# Three levels:
# - plain     = concise natural-language answers for non-programmers / QA.
# - technical = programmer-oriented code interpretation.
# - edit      = direct code-modification mode, only if the backend/tools allow it.
#
# The request may choose a mode, but it must be enabled here. Default is the
# safest external mode; open higher levels explicitly, e.g.
#   AGENT_ALLOWED_MODES=plain,technical
#   AGENT_ALLOWED_MODES=plain,technical,edit
AGENT_DEFAULT_MODE = operation_modes.normalize(
    os.environ.get("AGENT_DEFAULT_MODE", "plain")
)
AGENT_ALLOWED_MODES = operation_modes.parse_allowed(
    os.environ.get("AGENT_ALLOWED_MODES", AGENT_DEFAULT_MODE)
)

# Model used by the SDK backend (Bedrock model id). Falls back to the
# ANTHROPIC_MODEL env var that the Bedrock setup already provides.
SDK_MODEL = os.environ.get(
    "SDK_MODEL", os.environ.get("ANTHROPIC_MODEL", "us.anthropic.claude-opus-4-8")
)

# Bedrock proxy base URL for the SDK backend (the /bedrock path on the same
# gateway whose /v1 path serves the custom backend). The Claude Code CLI reads
# this via ANTHROPIC_BEDROCK_BASE_URL; we default it here so both backends point
# at the same proxy out of the box.
SDK_BEDROCK_BASE_URL = os.environ.get(
    "ANTHROPIC_BEDROCK_BASE_URL", "http://10.253.17.63:8090/bedrock"
)

# --- Agent loop ------------------------------------------------------------
# 16 rounds tolerates the enumeration-heavy questions (列出所有调用源, etc.)
# that routinely hit a 12-round ceiling in observed traces. With prompt caching,
# the per-round cost of late rounds is mostly cached input — the marginal cost
# of going 12 → 16 is much smaller than the answer-quality cliff at the cap.
MAX_ITERATIONS = int(os.environ.get("AGENT_MAX_ITERATIONS", "16"))
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0"))
LLM_TIMEOUT = float(os.environ.get("LLM_TIMEOUT", "120"))

# Retry transient LLM failures (rate limit / timeout / empty response) with
# litellm's built-in exponential backoff. 0 disables retries.
LLM_NUM_RETRIES = int(os.environ.get("LLM_NUM_RETRIES", "3"))

# Annotate the system message with Anthropic-style ``cache_control`` so the
# proxy can flip on prompt caching for the static prefix (system prompt + tool
# schemas). Anthropic / Bedrock honor it natively; non-Anthropic providers
# (Gemini, OpenAI proxies that don't pass it through) silently drop it.
LLM_PROMPT_CACHE = os.environ.get("LLM_PROMPT_CACHE", "1") not in ("0", "false", "False")

# Stuck detection: stop early if the agent repeats the same tool call this many
# times in a row (e.g. grepping the same pattern, or repeated errors). 0 = off.
STUCK_REPEAT_THRESHOLD = int(os.environ.get("STUCK_REPEAT_THRESHOLD", "3"))

# Observation masking: keep only the most recent N tool outputs in full when
# rebuilding messages; older ones are replaced with a one-line summary to keep
# the context from growing unbounded over a long session. 0 = keep everything.
# Empirically 3 is enough — by the time round N happens, outputs from round
# N-4 onward have been digested into the model's working state and the
# verbatim text just inflates the prompt (and breaks prefix caching).
OBS_KEEP_FULL = int(os.environ.get("OBS_KEEP_FULL", "3"))

# --- Tool output limits (keep tool results from blowing the context) -------
# read_file caps single-call body to MAX_READ_BYTES; 8 KiB ≈ 200 lines of dense
# code, comfortably above what the agent typically asks for (median ~73 lines in
# observed traces) and prevents an unbounded "end omitted" read from torching
# the round's prompt.
MAX_READ_BYTES = int(os.environ.get("MAX_READ_BYTES", "8000"))
MAX_GREP_MATCHES = int(os.environ.get("MAX_GREP_MATCHES", "100"))
# Enumeration modes (files / count) post-process down to one entry per file, so
# they can afford a much larger raw-match scan budget before the model loses
# fidelity. Keep this above what any popular symbol could plausibly produce.
MAX_GREP_FILES = int(os.environ.get("MAX_GREP_FILES", "400"))
MAX_LIST_ENTRIES = int(os.environ.get("MAX_LIST_ENTRIES", "300"))

# --- Offline index (方案 2) ------------------------------------------------
# SQLite symbol/FTS index. When present, find_symbol/grep_code use it (fast,
# exact); otherwise they fall back to live filesystem scanning. Build with
# `python -m code_agent.retrieval.indexer` / scripts/index.sh.
INDEX_DB_PATH = os.environ.get(
    "INDEX_DB_PATH",
    os.path.join(PROJECT_ROOT, "index", "code_index.db"),
)
# Set USE_INDEX=0 to force the live-scan fallback even if an index exists.
USE_INDEX = os.environ.get("USE_INDEX", "1") not in ("0", "false", "False")

# Entry short-circuit: answer precise "where is X defined" questions straight
# from the index, skipping the LLM (方案 2). Set USE_SHORTCUT=0 to disable.
USE_SHORTCUT = os.environ.get("USE_SHORTCUT", "1") not in ("0", "false", "False")

# --- Knowledge flywheel (方案 3) -------------------------------------------
# Precipitate answered questions into a SQLite knowledge base and recall related
# entries (as leads, re-verified) on later questions. Separate DB since it's
# written incrementally at query time.
KNOWLEDGE_DB_PATH = os.environ.get(
    "KNOWLEDGE_DB_PATH",
    os.path.join(PROJECT_ROOT, "index", "knowledge.db"),
)
# Master switch for the flywheel. Off by default until the recall hit-rate is
# validated (roadmap 方案 3 MVP); set USE_KNOWLEDGE=1 to enable.
USE_KNOWLEDGE = os.environ.get("USE_KNOWLEDGE", "0") not in ("0", "false", "False")

# Stable code-knowledge map injection. This is separate from the dynamic Q&A
# flywheel: markdown cards under docs/code-knowledge/<repo>/ are versioned
# source files and can safely be used as navigation hints by default.
CODE_KNOWLEDGE_MAP_ENABLED = os.environ.get("CODE_KNOWLEDGE_MAP_ENABLED", "1") not in (
    "0",
    "false",
    "False",
)
CODE_KNOWLEDGE_MAP_MAX_CARDS = int(os.environ.get("CODE_KNOWLEDGE_MAP_MAX_CARDS", "12"))
ASSERT_KNOWLEDGE_ENABLED = os.environ.get("ASSERT_KNOWLEDGE_ENABLED", "1") not in (
    "0",
    "false",
    "False",
)
ASSERT_KNOWLEDGE_MAX_ITEMS = int(os.environ.get("ASSERT_KNOWLEDGE_MAX_ITEMS", "4"))

# --- Service ---------------------------------------------------------------
SERVICE_PORT = int(os.environ.get("SERVICE_PORT", "8900"))
SERVICE_HOST = os.environ.get("SERVICE_HOST", "0.0.0.0")

# Concurrency governance for /ask and /diagnose (each runs a long LLM loop).
# At most MAX_CONCURRENCY run at once; up to MAX_QUEUE more may wait, others get
# 503; a single request is capped at REQUEST_TIMEOUT seconds (504 on overrun).
MAX_CONCURRENCY = int(os.environ.get("MAX_CONCURRENCY", "4"))
MAX_QUEUE = int(os.environ.get("MAX_QUEUE", "8"))
REQUEST_TIMEOUT = float(os.environ.get("REQUEST_TIMEOUT", "180"))

# Bound the in-memory /ask answer cache (LRU). 0 disables caching entirely.
CACHE_MAX_ENTRIES = int(os.environ.get("CACHE_MAX_ENTRIES", "512"))

# Per-request LLM interaction traces. Each agent request writes one JSONL file
# under logs/llm by default. Best-effort; write failures do not fail requests.
LLM_TRACE_ENABLED = os.environ.get("LLM_TRACE_ENABLED", "1") not in (
    "0",
    "false",
    "False",
)
LLM_TRACE_DIR = os.path.abspath(
    os.environ.get(
        "LLM_TRACE_DIR",
        os.path.join(PROJECT_ROOT, "logs", "llm"),
    )
)
LLM_TRACE_VIEW_MAX_FILES = int(os.environ.get("LLM_TRACE_VIEW_MAX_FILES", "200"))


def repo_names() -> list[str]:
    """Configured repo names. Without CODE_REPOS there is one legacy default."""
    return list(CODE_REPOS) if CODE_REPOS else [CODE_REPO_DEFAULT]


def resolve_repo_name(repo: str | None = None) -> str:
    """Resolve a requested repo name and validate it against CODE_REPOS."""
    name = (repo or _CURRENT_REPO.get() or CODE_REPO_DEFAULT).strip()
    if not name:
        name = CODE_REPO_DEFAULT
    if CODE_REPOS and name not in CODE_REPOS:
        raise ValueError(
            f"unknown repo {name!r}; available repos: {', '.join(repo_names())}"
        )
    if not CODE_REPOS and name != CODE_REPO_DEFAULT:
        raise ValueError(f"unknown repo {name!r}; only {CODE_REPO_DEFAULT!r} is configured")
    return name


def current_repo() -> CodeRepo:
    """Return the repo selected for the current request/context."""
    name = resolve_repo_name()
    if CODE_REPOS:
        return CODE_REPOS[name]
    # Legacy single-repo mode stays dynamic so tests that monkeypatch
    # TARGET_CODE_PATH / INDEX_DB_PATH keep working.
    return CodeRepo(
        name=name,
        path=TARGET_CODE_PATH,
        index_db_path=INDEX_DB_PATH,
        knowledge_db_path=KNOWLEDGE_DB_PATH,
        profile_path=_repo_storage_path(name, "profile.json"),
    )


def current_target_code_path() -> str:
    return current_repo().path


def current_index_db_path() -> str:
    return current_repo().index_db_path


def current_knowledge_db_path() -> str:
    return current_repo().knowledge_db_path


def current_profile_path() -> str:
    return current_repo().profile_path


@contextlib.contextmanager
def use_repo(repo: str | None):
    """Temporarily select a repo for this request/thread/task."""
    name = resolve_repo_name(repo)
    token = _CURRENT_REPO.set(name)
    try:
        yield current_repo()
    finally:
        _CURRENT_REPO.reset(token)

def require_api_key() -> str:
    """Return LLM_API_KEY or raise a clear error if it isn't configured.

    Called at the first LLM request so the CLI/service fail fast with an
    actionable message instead of a confusing 401 from the proxy.
    """
    if not LLM_API_KEY:
        raise RuntimeError(
            "LLM_API_KEY is not set. Export it (or put it in a .env file) — "
            "see .env.example. The token is no longer hardcoded in config.py."
        )
    return LLM_API_KEY


SYSTEM_PROMPT_BASE = """\
你是一个代码理解助手，专门回答关于游戏项目代码库的问题，涵盖游戏服务器、战斗、客户端、引擎等模块。
你不能直接看到代码，必须通过提供的工具来检索：

- grep_code(pattern, path, output_mode, context, head_limit)  搜索代码
- glob(pattern, path, head_limit)                             按文件名/路径模式列文件（如 '**/Monster*.cpp'）
- read_file(path, start, end)                                 读取某个文件指定行范围
- list_dir(path)                                              列出目录结构
- find_symbol(name)                                           定位类/函数的定义位置
- repo_overview()                                             查看项目概览/模块导航
- resolve_frame(frame)                                        把 crash 栈帧映射到代码定义
- find_log_source(message)                                    根据运行时日志反查打印点
- find_assert_context(message, context)                       根据断言/错误日志定位 assert/check 上下文

工作方式（**严格按这个顺序选工具，能省 token 就别多花**）：
1. **只看文件名能解决的问题**（"有哪些 *.lua 脚本"、"Monster 相关文件"）：用 glob，最便宜。
2. **枚举型问题**（"哪些模块/文件用到 X"、"列出所有调用源"）：先用 grep_code(pattern, output_mode="files")，只看文件名列表往往就能分类；不够再 output_mode="count" 看分布；只有需要看具体代码时才用 content。
3. **理解型问题**（"X 是怎么实现的"、"流程是什么"）：用 grep_code(pattern, output_mode="content", context=3) 一次拿到命中前后若干行，**通常无需再调 read_file**。
4. **断言失败/ASSERT/CHECK/错误日志定位**：先用 find_assert_context(message)，拿到断言候选和上下文；运行时 file:line 可能不准，只能当弱线索，必须结合上下文确认；若没命中，再用 find_log_source 或 grep_code。
5. read_file 只在以下情况用：需要看完整函数体；grep/assert 上下文不够。**必须显式传 start/end**，单次窗口建议 30..150 行（默认上限 8KB ≈ 200 行）；想再多请分多次读连续片段。
6. **同一轮里可以并行发起多个 tool_calls**：独立的搜索/读取一次性全部列出，不要每轮只调一个工具——这能显著减少总轮数。
7. 所有路径都相对于目标代码库根目录（不要使用绝对路径或 .. 越界）。
8. 收集到足够信息后，用中文清晰地回答问题，并在合适时引用文件路径和行号。
如果代码库中确实找不到相关内容，如实说明，不要编造。
"""


def system_prompt_for_mode(mode: str | None = None) -> str:
    """Return the system prompt for an enabled operation mode."""
    resolved = operation_modes.resolve(
        mode, default=AGENT_DEFAULT_MODE, allowed=AGENT_ALLOWED_MODES
    )
    return operation_modes.prompt(SYSTEM_PROMPT_BASE, resolved)

# Backwards-compatible default prompt used by tests/docs and older callers.
SYSTEM_PROMPT = system_prompt_for_mode(AGENT_DEFAULT_MODE)
