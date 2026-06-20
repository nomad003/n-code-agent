"""Response/operation mode policy shared by all entrypoints.

The service has three externally selectable levels. A caller may request a
level, but the agent must explicitly enable it via config before it is allowed.
"""
from __future__ import annotations


MODES = ("plain", "technical", "edit")
MODE_LABELS = {
    "plain": "level 1 / non-programmer",
    "technical": "level 2 / programmer",
    "edit": "level 3 / direct code modification",
}

_ALIASES = {
    "1": "plain",
    "level1": "plain",
    "non_programmer": "plain",
    "non-programmer": "plain",
    "qa": "plain",
    "planner": "plain",
    "plain": "plain",
    "simple": "plain",
    "2": "technical",
    "level2": "technical",
    "programmer": "technical",
    "developer": "technical",
    "technical": "technical",
    "tech": "technical",
    "3": "edit",
    "level3": "edit",
    "modify": "edit",
    "write": "edit",
    "edit": "edit",
}


class ModeError(ValueError):
    """Raised when a requested mode is unknown or disabled."""


def normalize(mode: str | None) -> str:
    """Normalize a user/config supplied mode string."""
    key = (mode or "plain").strip().lower().replace(" ", "_")
    key = key.replace("-", "_")
    normalized = _ALIASES.get(key)
    if normalized is None:
        raise ModeError(
            f"unknown operation mode {mode!r}; allowed names are: {', '.join(MODES)}"
        )
    return normalized


def parse_allowed(raw: str | None) -> tuple[str, ...]:
    """Parse a comma-separated allowlist. Empty config means plain only."""
    if not raw or not raw.strip():
        return ("plain",)
    out: list[str] = []
    for part in raw.split(","):
        mode = normalize(part)
        if mode not in out:
            out.append(mode)
    return tuple(out) or ("plain",)


def resolve(requested: str | None, *, default: str, allowed: tuple[str, ...]) -> str:
    """Return the requested/default mode if it is enabled for this agent."""
    mode = normalize(requested or default)
    if mode not in allowed:
        raise ModeError(
            f"operation mode {mode!r} is disabled for this agent; "
            f"enabled modes: {', '.join(allowed)}"
        )
    return mode


def response_rules(mode: str) -> str:
    """Mode-specific prompt rules appended to the shared code-search prompt."""
    mode = normalize(mode)
    if mode == "plain":
        return """\
对外回答格式（第 1 档：面向非程序员/策划/QA）：
1. 只给简单、精确、结构化的自然语言结论，优先用短表格或短列表。
2. 严禁输出任何代码片段、伪代码、命令行、JSON 示例、配置样例或可复制执行的实现内容。
3. 即使用户要求代码或示例，也只用结构化文字描述字段、能力、约束、流程和注意事项。
4. 用户只问能力、接口、结论、排查方向时，只描述结构、用途、约束、下一步，不展开底层实现。
5. 如果信息不足，先说明缺口和需要的输入，不要用长篇解释填充。
"""
    if mode == "technical":
        return """\
对外回答格式（第 2 档：面向程序员解读）：
1. 给出面向程序员的代码级解释，可以引用类、函数、字段、调用链、文件路径和行号。
2. 可以说明关键实现逻辑、边界条件、风险点、测试建议和改造方案。
3. 不直接修改代码；如需改动，只说明改动点、影响范围和验证方式。
4. 代码片段只在确有助于解释时少量引用，避免整段复制文件内容。
"""
    return """\
对外回答格式（第 3 档：直接代码修改）：
1. 可以处理明确的代码修改目标，输出面向实现的结论、变更说明和验证结果。
2. 修改前先定位相关代码和影响范围；修改后说明改了哪些文件、为什么改、如何验证。
3. 当前服务只会启用 agent 配置允许的写入能力；没有写入工具时，应明确说明只能给出改动方案。
4. 不要绕过沙箱、不要修改目标代码库之外的路径。
"""


def prompt(base_prompt: str, mode: str) -> str:
    """Build the full system prompt for a mode."""
    return base_prompt.rstrip() + "\n\n" + response_rules(mode).rstrip() + "\n"
