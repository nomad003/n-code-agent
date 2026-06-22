"""Claude Agent SDK backend (selected by AGENT_BACKEND=sdk).

This wraps the SAME sandboxed tools from ``code_agent.retrieval.tools`` as in-process SDK tools
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

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

from .. import config
from ..observability import llm_trace
from ..retrieval import tools
from . import operation_modes
from . import question_intent

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


@tool(
    "glob",
    "按 fnmatch/glob 模式列出文件路径（按 mtime 倒序）。枚举文件型问题首选。",
    {"pattern": str, "path": str, "head_limit": int},
)
async def _glob(args):
    return _text(tools.dispatch("glob", args))


@tool("find_symbol", "查找某个类/函数/类型的定义位置。", {"name": str})
async def _find_symbol(args):
    return _text(tools.dispatch("find_symbol", args))


@tool("repo_overview", "查看已缓存的代码库导航/项目概览/常用模块候选。", {})
async def _repo_overview(args):
    return _text(tools.dispatch("repo_overview", args))


_SERVER = create_sdk_mcp_server(
    name="code",
    version="1.0.0",
    tools=[_grep_code, _read_file, _list_dir, _glob, _find_symbol, _repo_overview],
)

# Tool names are namespaced as mcp__<server>__<tool> once registered.
_ALLOWED_TOOLS = [
    "mcp__code__grep_code",
    "mcp__code__read_file",
    "mcp__code__list_dir",
    "mcp__code__glob",
    "mcp__code__find_symbol",
    "mcp__code__repo_overview",
]


def _bedrock_env() -> dict:
    """Bedrock routing vars for the CLI.

    Defaults come from config (so the SDK backend points at the same proxy as
    the custom backend), and any matching env var overrides them.
    """
    env = {
        "CLAUDE_CODE_USE_BEDROCK": "1",
        "ANTHROPIC_BEDROCK_BASE_URL": config.SDK_BEDROCK_BASE_URL,
        "CLAUDE_CODE_SKIP_BEDROCK_AUTH": "1",
        "AWS_REGION": "us-east-1",
        # The proxy authenticates with the same token the custom backend uses.
        "ANTHROPIC_AUTH_TOKEN": config.LLM_API_KEY or os.environ.get("ANTHROPIC_AUTH_TOKEN", ""),
    }
    # Let an explicitly-exported env var win over our defaults.
    for key in list(env):
        if os.environ.get(key):
            env[key] = os.environ[key]
    return env


def _resolve_cli_path() -> str | None:
    """Prefer the vendored CLI binary; else let the SDK find one on PATH."""
    if os.path.isfile(_VENDORED_CLI) and os.access(_VENDORED_CLI, os.X_OK):
        return _VENDORED_CLI
    return None  # SDK falls back to the bundled/`claude`-on-PATH binary


def _trace_error(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"


def _prompt_context_block(
    key: str,
    title: str,
    text: str,
    *,
    injected: bool | None = None,
    enabled: bool = True,
    reason: str = "",
    error: str = "",
    sources: list[str] | None = None,
    order: int = 0,
    audit: bool = False,
) -> dict:
    body = text or ""
    return {
        "key": key,
        "title": title,
        "order": order,
        "enabled": bool(enabled),
        "injected": bool(body) if injected is None else bool(injected),
        "chars": len(body),
        "sources": sources or [],
        "reason": reason,
        "error": error,
        "audit": bool(audit),
        "content": body,
    }


def _system_prompt_with_profile(mode: str) -> tuple[str, str, str, str]:
    system_prompt = config.system_prompt_for_mode(mode)
    profile_error = ""
    profile_reason = ""
    try:
        from ..retrieval import repo_profile

        profile_text = repo_profile.format_for_prompt()
    except Exception as exc:
        profile_text = ""
        profile_error = _trace_error(exc)
    if not profile_text and not profile_error:
        profile_reason = "repo overview empty"
    if profile_text:
        system_prompt = system_prompt + "\n\n" + profile_text
    return system_prompt, profile_text, profile_error, profile_reason


def _trace_sdk_context(
    *,
    question: str,
    mode: str,
    trace: llm_trace.LLMTrace | None,
    system_prompt: str,
    profile_text: str,
    profile_error: str,
    profile_reason: str,
) -> None:
    if not trace:
        return
    resolved_question_type = question_intent.classify(question)
    output_mode_prompt = operation_modes.response_rules(mode).rstrip()
    sdk_reason = "sdk backend does not inject this custom context block"
    context_errors = {"repo_overview": profile_error} if profile_error else {}
    context_reasons = {
        "repo_overview": profile_reason,
        "intent_prompt": sdk_reason,
        "knowledge_graph": sdk_reason,
        "module_cards": sdk_reason,
        "assert_knowledge": sdk_reason,
        "recalled_qa": sdk_reason,
    }
    context_reasons = {key: value for key, value in context_reasons.items() if value}
    assembly_order = [
        "base_prompt",
        "intent_prompt",
        "repo_overview",
        "knowledge_graph",
        "module_cards",
        "assert_knowledge",
        "recalled_qa",
        "output_mode",
    ]
    blocks = [
        _prompt_context_block(
            "base_prompt",
            "基础系统提示词",
            config.SYSTEM_PROMPT_BASE,
            injected=True,
            order=10,
        ),
        _prompt_context_block(
            "intent_prompt",
            "当前问题类型提示词",
            "",
            injected=False,
            reason=context_reasons["intent_prompt"],
            sources=[resolved_question_type],
            order=20,
        ),
        _prompt_context_block(
            "repo_overview",
            "Repo Overview",
            profile_text,
            reason=profile_reason,
            error=profile_error,
            order=30,
        ),
        _prompt_context_block(
            "knowledge_graph",
            "代码知识图谱摘要",
            "",
            injected=False,
            reason=context_reasons["knowledge_graph"],
            order=40,
        ),
        _prompt_context_block(
            "module_cards",
            "命中的模块知识卡",
            "",
            injected=False,
            reason=context_reasons["module_cards"],
            order=50,
        ),
        _prompt_context_block(
            "assert_knowledge",
            "Assert 知识",
            "",
            injected=False,
            reason=context_reasons["assert_knowledge"],
            order=60,
        ),
        _prompt_context_block(
            "recalled_qa",
            "历史问答沉淀",
            "",
            injected=False,
            reason=context_reasons["recalled_qa"],
            order=70,
        ),
        _prompt_context_block(
            "output_mode",
            "plain/technical 模式输出要求",
            output_mode_prompt,
            injected=True,
            sources=[mode],
            order=80,
        ),
        _prompt_context_block(
            "combined_system_prompt",
            "最终 System Prompt（组装后）",
            system_prompt,
            injected=True,
            sources=["sdk_request.system_prompt"],
            order=90,
            audit=True,
        ),
    ]
    trace.write(
        "knowledge_context_injected",
        blocks=blocks,
        assembly_order=assembly_order,
        backend="sdk",
        mode=mode,
        question_type=resolved_question_type,
        repo=config.current_repo().name,
        target_code_path=config.current_target_code_path(),
        with_tools=True,
        prompt_cache_enabled=False,
        combined_system_chars=len(system_prompt or ""),
        context_errors=context_errors,
        context_reasons=context_reasons,
        code_knowledge_map_enabled=config.CODE_KNOWLEDGE_MAP_ENABLED,
        code_knowledge_map_injected=False,
        code_knowledge_map_chars=0,
        code_knowledge_map_cards=[],
        module_cards_injected=False,
        module_cards_chars=0,
        module_cards=[],
        assert_context_injected=False,
        assert_context_chars=0,
        recalled_context_injected=False,
        recalled_context_chars=0,
    )


def _options(mode: str = "plain", *, system_prompt: str | None = None) -> ClaudeAgentOptions:
    if system_prompt is None:
        system_prompt, _profile_text, _profile_error, _profile_reason = (
            _system_prompt_with_profile(mode)
        )
    opts = ClaudeAgentOptions(
        system_prompt=system_prompt,
        model=config.SDK_MODEL,
        max_turns=config.MAX_ITERATIONS,
        cwd=config.current_target_code_path(),
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


async def _ask_async(
    question: str,
    *,
    verbose: bool = False,
    mode: str = "plain",
    trace: llm_trace.LLMTrace | None = None,
) -> str:
    parts: list[str] = []
    system_prompt, profile_text, profile_error, profile_reason = _system_prompt_with_profile(mode)
    _trace_sdk_context(
        question=question,
        mode=mode,
        trace=trace,
        system_prompt=system_prompt,
        profile_text=profile_text,
        profile_error=profile_error,
        profile_reason=profile_reason,
    )
    if trace:
        trace.write(
            "sdk_request",
            prompt=question,
            system_prompt=system_prompt,
            mode=mode,
            model=config.SDK_MODEL,
            max_turns=config.MAX_ITERATIONS,
            allowed_tools=_ALLOWED_TOOLS,
        )
    async for message in query(prompt=question, options=_options(mode, system_prompt=system_prompt)):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    parts.append(block.text)
                    if trace:
                        trace.write("sdk_text", text=block.text)
                elif type(block).__name__ == "ToolUseBlock":
                    if verbose:
                        print(f"  [tool] {block.name}({block.input})")
                    if trace:
                        trace.write(
                            "sdk_tool_use",
                            name=getattr(block, "name", ""),
                            input=getattr(block, "input", {}),
                        )
        elif isinstance(message, ResultMessage):
            # On success the final text is also exposed here; prefer streamed
            # text, but fall back to result if we collected nothing.
            if trace:
                trace.write("sdk_result", result=getattr(message, "result", None))
            if not parts and getattr(message, "result", None):
                parts.append(message.result)
    return "".join(parts).strip()


def answer(
    question: str,
    *,
    verbose: bool = False,
    mode: str = "plain",
    trace: llm_trace.LLMTrace | None = None,
) -> str:
    """Sync wrapper matching agent.answer()'s contract."""
    return asyncio.run(_ask_async(question, verbose=verbose, mode=mode, trace=trace))
