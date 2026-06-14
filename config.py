"""Global configuration for the code-comprehension service.

All values can be overridden by environment variables. LLM access always goes
through litellm to the mushigen proxy — never call a provider SDK directly.
"""
import os

# --- LLM -------------------------------------------------------------------
LLM_MODEL = os.environ.get("LLM_MODEL", "vertex_ai/gemini-3.5-flash")
# The mushigen proxy is an OpenAI-compatible gateway. litellm must route every
# model through it as an "openai/" custom endpoint — otherwise a "vertex_ai/"
# prefix triggers litellm's native Google Cloud auth (which we don't use) and
# the request never hits the proxy.
LLM_API_BASE = os.environ.get(
    "LLM_API_BASE", "https://mushigen.comet.scopelyai.com/v1"
)
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
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "target_code"),
    )
)

# --- Agent backend ---------------------------------------------------------
# "custom" = the litellm tool-calling loop (default, model-agnostic via proxy).
# "sdk"    = the Claude Agent SDK loop (claude-agent-sdk + Claude Code CLI,
#            routed through Bedrock env vars). Both reuse the same sandboxed
#            tools in tools.py and expose the same agent.answer() interface.
AGENT_BACKEND = os.environ.get("AGENT_BACKEND", "custom").strip().lower()

# Model used by the SDK backend (Bedrock model id). Falls back to the
# ANTHROPIC_MODEL env var that the Bedrock setup already provides.
SDK_MODEL = os.environ.get(
    "SDK_MODEL", os.environ.get("ANTHROPIC_MODEL", "us.anthropic.claude-opus-4-8")
)

# --- Agent loop ------------------------------------------------------------
MAX_ITERATIONS = int(os.environ.get("AGENT_MAX_ITERATIONS", "12"))
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0"))
LLM_TIMEOUT = float(os.environ.get("LLM_TIMEOUT", "120"))

# --- Tool output limits (keep tool results from blowing the context) -------
MAX_READ_BYTES = int(os.environ.get("MAX_READ_BYTES", "20000"))
MAX_GREP_MATCHES = int(os.environ.get("MAX_GREP_MATCHES", "100"))
MAX_LIST_ENTRIES = int(os.environ.get("MAX_LIST_ENTRIES", "300"))

# --- Service ---------------------------------------------------------------
SERVICE_PORT = int(os.environ.get("SERVICE_PORT", "8900"))
SERVICE_HOST = os.environ.get("SERVICE_HOST", "0.0.0.0")

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


SYSTEM_PROMPT = """\
你是一个代码理解助手，专门回答关于游戏项目代码库的问题，涵盖游戏服务器、战斗、客户端、引擎等模块。
你不能直接看到代码，必须通过提供的工具来检索：

- grep_code(pattern, path)    搜索代码中的符号或关键字
- read_file(path, start, end) 读取某个文件的内容（按行）
- list_dir(path)              列出目录结构
- find_symbol(name)           定位类/函数的定义位置

工作方式：
1. 先用 find_symbol / grep_code / list_dir 定位相关代码，再用 read_file 读取细节。
2. 多次调用工具，逐步收集证据，不要凭空猜测。
3. 所有路径都相对于目标代码库根目录（不要使用绝对路径或 .. 越界）。
4. 收集到足够信息后，用中文清晰地回答问题，并在合适时引用文件路径和行号。
如果代码库中确实找不到相关内容，如实说明，不要编造。
"""
