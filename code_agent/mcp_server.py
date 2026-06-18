"""MCP server exposing the code-comprehension agent to other MCP clients.

Transport: streamable-http (the current MCP HTTP transport). Exposes one
high-level tool, ``ask_codebase(question)``, which runs the full agent loop
(via the configured AGENT_BACKEND) and returns a natural-language answer.

Run:
    python -m code_agent.mcp_server                 # streamable-http on MCP_HOST:MCP_PORT
    MCP_PORT=8901 python -m code_agent.mcp_server

The MCP endpoint is served at the path ``/mcp`` (configurable via MCP_PATH).
Other services connect with an MCP streamable-http client pointed at
    http://<host>:<port>/mcp

This is a thin adapter: it reuses agent.answer() and config, so it honours the
same backend selection, sandboxed tools, and target codebase as the HTTP/CLI
entrypoints.
"""
import logging
import os
import time
from logging.handlers import RotatingFileHandler

from mcp.server.fastmcp import FastMCP

from . import agent
from . import config
from . import operation_modes
from . import response_policy

MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.environ.get("MCP_PORT", "8901"))
MCP_PATH = os.environ.get("MCP_PATH", "/mcp")

# Log file path. Defaults to <project>/logs/mcp.log; override with MCP_LOG_FILE.
_DEFAULT_LOG = os.path.join(config.PROJECT_ROOT, "logs", "mcp.log")
MCP_LOG_FILE = os.environ.get("MCP_LOG_FILE", _DEFAULT_LOG)

_fmt = logging.Formatter("%(asctime)s [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
_handlers: list[logging.Handler] = [logging.StreamHandler()]  # console (stdout)
try:
    os.makedirs(os.path.dirname(MCP_LOG_FILE), exist_ok=True)
    # 5 MB per file, keep 3 backups.
    _handlers.append(RotatingFileHandler(MCP_LOG_FILE, maxBytes=5_000_000, backupCount=3, encoding="utf-8"))
except OSError as exc:  # fall back to console-only if the dir isn't writable
    print(f"[mcp] WARN: cannot open log file {MCP_LOG_FILE}: {exc}; console only")
    MCP_LOG_FILE = None
for _h in _handlers:
    _h.setFormatter(_fmt)
logging.basicConfig(level=logging.INFO, handlers=_handlers)
log = logging.getLogger("mcp.ask")

mcp = FastMCP(
    "code-agent",
    instructions=(
        "回答关于目标游戏代码库（服务器/战斗/客户端/引擎）的问题。"
        "调用 ask_codebase 传入一个自然语言问题，返回解释性的答案。"
    ),
    host=MCP_HOST,
    port=MCP_PORT,
    streamable_http_path=MCP_PATH,
    # Stateless: each call is independent, so the server scales and needs no
    # client-side session affinity — a good fit for a stateless Q&A tool.
    stateless_http=True,
    json_response=True,
)


@mcp.tool()
def ask_codebase(question: str, mode: str = "", repo: str = "") -> str:
    """回答关于目标代码库的自然语言问题。

    内部运行完整的 agent 循环（grep/read/list/find_symbol 工具检索 + LLM），
    返回中文解释，必要时附带文件路径和行号。

    Args:
        question: 要询问的问题，例如 "SceneMgr 是做什么的？"。
        mode: 回答/操作等级：plain（非程序员）、technical（程序员解读）、edit（直接修改）；不传则使用 agent 默认模式。
        repo: 代码库名称；不传则使用默认仓库。
    """
    question = (question or "").strip()
    if not question:
        log.info("ask_codebase | 空问题，已拒绝")
        return "问题不能为空。"
    try:
        mode = operation_modes.resolve(
            mode, default=config.AGENT_DEFAULT_MODE, allowed=config.AGENT_ALLOWED_MODES
        )
    except operation_modes.ModeError as exc:
        log.info("ask_codebase | 模式拒绝: %s", exc)
        return f"模式不可用：{exc}"
    try:
        repo_name = config.resolve_repo_name(repo or None)
    except ValueError as exc:
        log.info("ask_codebase | 仓库拒绝: %s", exc)
        return f"仓库不可用：{exc}"
    # agent.answer is synchronous; FastMCP runs sync tools in a worker thread,
    # so this does not block the event loop.
    log.info("ask_codebase | 收到提问 (repo=%s, mode=%s): %s", repo_name, mode, question)
    start = time.monotonic()
    try:
        answer = agent.answer(question, mode=mode, repo=repo_name)
    except Exception as exc:
        elapsed = time.monotonic() - start
        log.warning("ask_codebase | 失败 (%.1fs): %s", elapsed, exc)
        raise
    elapsed = time.monotonic() - start
    log.info("ask_codebase | 完成 (%.1fs, 答案 %d 字): %s", elapsed, len(answer), question)
    return response_policy.enforce(answer, mode=mode)


@mcp.tool()
def diagnose_crash(backtrace: str, log_snippet: str = "", repo: str = "") -> str:
    """分析崩溃栈或日志片段，结合代码库定位根因。

    有 backtrace 时逐帧把函数映射到代码定义（复用符号索引，自动收窄同名候选）；
    有日志片段时反查打印点。随后用 agent 读取相关代码、分析最可能的根因与排查方向。

    Args:
        backtrace: 可选，gdb 风格的崩溃栈文本（如 `gdb bt` 输出）。
        log_snippet: 可选，相关日志片段。可单独提供，用于纯日志诊断。
        repo: 代码库名称；不传则使用默认仓库。
    """
    backtrace = backtrace or ""
    log_snippet = log_snippet or ""
    if not backtrace.strip() and not log_snippet.strip():
        return "backtrace 和 log_snippet 不能同时为空。"
    from . import diagnose as diag
    try:
        repo_name = config.resolve_repo_name(repo or None)
    except ValueError as exc:
        return f"仓库不可用：{exc}"

    log.info(
        "diagnose_crash | 收到 repo=%s backtrace (%d 字), log_snippet (%d 字)",
        repo_name,
        len(backtrace),
        len(log_snippet),
    )
    start = time.monotonic()
    try:
        with config.use_repo(repo_name):
            result = diag.diagnose(backtrace, extra_log=log_snippet)
    except Exception as exc:
        log.warning("diagnose_crash | 失败 (%.1fs): %s", time.monotonic() - start, exc)
        raise
    elapsed = time.monotonic() - start
    log.info(
        "diagnose_crash | 完成 (%.1fs, %d/%d 帧已定位)",
        elapsed, result["resolved"], result["total_frames"],
    )
    return response_policy.enforce(result["answer"], mode="technical")


def main() -> None:
    print(
        f"[mcp] code-agent MCP server (backend={config.AGENT_BACKEND}) "
        f"on http://{MCP_HOST}:{MCP_PORT}{MCP_PATH}"
    )
    print(f"[mcp] 日志文件: {MCP_LOG_FILE or '(仅控制台)'}")
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
