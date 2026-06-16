"""MCP server exposing the code-comprehension agent to other MCP clients.

Transport: streamable-http (the current MCP HTTP transport). Exposes one
high-level tool, ``ask_codebase(question)``, which runs the full agent loop
(via the configured AGENT_BACKEND) and returns a natural-language answer.

Run:
    python3 mcp_server.py                 # streamable-http on MCP_HOST:MCP_PORT
    MCP_PORT=8901 python3 mcp_server.py

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

import agent
import config

MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.environ.get("MCP_PORT", "8901"))
MCP_PATH = os.environ.get("MCP_PATH", "/mcp")

# Log file path. Defaults to <project>/logs/mcp.log; override with MCP_LOG_FILE.
_DEFAULT_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "mcp.log")
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
def ask_codebase(question: str) -> str:
    """回答关于目标代码库的自然语言问题。

    内部运行完整的 agent 循环（grep/read/list/find_symbol 工具检索 + LLM），
    返回中文解释，必要时附带文件路径和行号。

    Args:
        question: 要询问的问题，例如 "SceneMgr 是做什么的？"。
    """
    question = (question or "").strip()
    if not question:
        log.info("ask_codebase | 空问题，已拒绝")
        return "问题不能为空。"
    # agent.answer is synchronous; FastMCP runs sync tools in a worker thread,
    # so this does not block the event loop.
    log.info("ask_codebase | 收到提问: %s", question)
    start = time.monotonic()
    try:
        answer = agent.answer(question)
    except Exception as exc:
        elapsed = time.monotonic() - start
        log.warning("ask_codebase | 失败 (%.1fs): %s", elapsed, exc)
        raise
    elapsed = time.monotonic() - start
    log.info("ask_codebase | 完成 (%.1fs, 答案 %d 字): %s", elapsed, len(answer), question)
    return answer


@mcp.tool()
def diagnose_crash(backtrace: str, log_snippet: str = "") -> str:
    """分析崩溃栈（coredump backtrace），结合代码库定位根因。

    逐帧把函数映射到代码定义（复用符号索引，自动收窄同名候选），再用 agent
    读取相关代码、分析最可能的崩溃原因与排查方向。

    Args:
        backtrace: gdb 风格的崩溃栈文本（如 `gdb bt` 输出）。
        log_snippet: 可选的相关日志片段，作为额外上下文。
    """
    if not (backtrace or "").strip():
        return "backtrace 不能为空。"
    import diagnose as diag

    log.info("diagnose_crash | 收到 backtrace (%d 字)", len(backtrace))
    start = time.monotonic()
    try:
        result = diag.diagnose(backtrace, extra_log=log_snippet)
    except Exception as exc:
        log.warning("diagnose_crash | 失败 (%.1fs): %s", time.monotonic() - start, exc)
        raise
    elapsed = time.monotonic() - start
    log.info(
        "diagnose_crash | 完成 (%.1fs, %d/%d 帧已定位)",
        elapsed, result["resolved"], result["total_frames"],
    )
    return result["answer"]


def main() -> None:
    print(
        f"[mcp] code-agent MCP server (backend={config.AGENT_BACKEND}) "
        f"on http://{MCP_HOST}:{MCP_PORT}{MCP_PATH}"
    )
    print(f"[mcp] 日志文件: {MCP_LOG_FILE or '(仅控制台)'}")
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
