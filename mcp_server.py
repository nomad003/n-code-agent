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
import os

from mcp.server.fastmcp import FastMCP

import agent
import config

MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.environ.get("MCP_PORT", "8901"))
MCP_PATH = os.environ.get("MCP_PATH", "/mcp")

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
        return "问题不能为空。"
    # agent.answer is synchronous; FastMCP runs sync tools in a worker thread,
    # so this does not block the event loop.
    return agent.answer(question)


def main() -> None:
    print(
        f"[mcp] code-agent MCP server (backend={config.AGENT_BACKEND}) "
        f"on http://{MCP_HOST}:{MCP_PORT}{MCP_PATH}"
    )
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
