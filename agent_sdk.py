"""Claude Agent SDK backend (selected by AGENT_BACKEND=sdk).

This wraps the SAME sandboxed tools from ``tools.py`` as in-process SDK tools
(``@tool`` + an SDK MCP server), so the security guarantees (path sandbox,
output caps) are identical to the custom backend. The built-in Read/Grep/Bash
tools are disabled — the model may use only our four code-search tools.

The SDK talks to Claude through the Claude Code CLI, routed to Bedrock by the
``CLAUDE_CODE_USE_BEDROCK`` / ``ANTHROPIC_BEDROCK_BASE_URL`` / ``ANTHROPIC_AUTH_TOKEN``
environment variables. We pass them explicitly via ``options.env`` so the
backend works even if the parent process didn't export them.
"""
import asyncio
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
# Vendored Claude Code CLI (linux-x64), checked in via Git LFS so the project
# is self-contained for migration. Falls back to the system `claude` on PATH.
_VENDORED_CLI = os.path.join(
    _HERE,
    "vendor",
    "claude-cli",
    "node_modules",
    "@anthropic-ai",
    "claude-code-linux-x64",
    "claude",
)

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    create_sdk_mcp_server,
    query,
    tool,
)

import config
import tools

# --- Wrap the existing sandboxed tools as SDK tools ------------------------
# Each delegates to tools.dispatch(), which enforces the path sandbox and the
# output-size caps. We return the dispatch string verbatim as a text block.


def _text(result: str) -> dict:
    return {"content": [{"type": "text", "text": result}]}


@tool(
    "grep_code",
    "在目标代码库中按正则搜索符号或关键字，返回 文件:行号: 内容。",
    {"pattern": str, "path": str},
)
async def _grep_code(args):
    return _text(tools.dispatch("grep_code", args))


@tool(
    "read_file",
    "读取某文件的指定行范围（1-based，含端点）。",
    {"path": str, "start": int, "end": int},
)
async def _read_file(args):
    return _text(tools.dispatch("read_file", args))


@tool("list_dir", "列出某个目录下的条目（单层），目录以 / 结尾。", {"path": str})
async def _list_dir(args):
    return _text(tools.dispatch("list_dir", args))


@tool("find_symbol", "查找某个类/函数/类型的定义位置。", {"name": str})
async def _find_symbol(args):
    return _text(tools.dispatch("find_symbol", args))


_SERVER = create_sdk_mcp_server(
    name="code",
    version="1.0.0",
    tools=[_grep_code, _read_file, _list_dir, _find_symbol],
)

# Tool names are namespaced as mcp__<server>__<tool> once registered.
_ALLOWED_TOOLS = [
    "mcp__code__grep_code",
    "mcp__code__read_file",
    "mcp__code__list_dir",
    "mcp__code__find_symbol",
]


def _bedrock_env() -> dict:
    """Bedrock routing vars for the CLI, sourced from the current environment."""
    keys = (
        "CLAUDE_CODE_USE_BEDROCK",
        "ANTHROPIC_BEDROCK_BASE_URL",
        "CLAUDE_CODE_SKIP_BEDROCK_AUTH",
        "AWS_REGION",
        "ANTHROPIC_AUTH_TOKEN",
    )
    return {k: os.environ[k] for k in keys if k in os.environ}


def _resolve_cli_path() -> str | None:
    """Prefer the vendored CLI binary; else let the SDK find one on PATH."""
    if os.path.isfile(_VENDORED_CLI) and os.access(_VENDORED_CLI, os.X_OK):
        return _VENDORED_CLI
    return None  # SDK falls back to the bundled/`claude`-on-PATH binary


def _options() -> ClaudeAgentOptions:
    opts = ClaudeAgentOptions(
        system_prompt=config.SYSTEM_PROMPT,
        model=config.SDK_MODEL,
        max_turns=config.MAX_ITERATIONS,
        cwd=config.TARGET_CODE_PATH,
        mcp_servers={"code": _SERVER},
        allowed_tools=_ALLOWED_TOOLS,
        # Block built-ins so the model is confined to our sandboxed tools.
        disallowed_tools=["Read", "Grep", "Glob", "Bash", "Write", "Edit"],
        permission_mode="bypassPermissions",
        env=_bedrock_env(),
    )
    cli = _resolve_cli_path()
    if cli:
        opts.cli_path = cli
    return opts


async def _ask_async(question: str, *, verbose: bool = False) -> str:
    parts: list[str] = []
    async for message in query(prompt=question, options=_options()):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    parts.append(block.text)
                elif verbose and type(block).__name__ == "ToolUseBlock":
                    print(f"  [tool] {block.name}({block.input})")
        elif isinstance(message, ResultMessage):
            # On success the final text is also exposed here; prefer streamed
            # text, but fall back to result if we collected nothing.
            if not parts and getattr(message, "result", None):
                parts.append(message.result)
    return "".join(parts).strip()


def answer(question: str, *, verbose: bool = False) -> str:
    """Sync wrapper matching agent.answer()'s contract."""
    return asyncio.run(_ask_async(question, verbose=verbose))
