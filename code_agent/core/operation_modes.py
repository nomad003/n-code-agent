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
1. 采用渐进披露：首答只给简单、精确、结构化的整体框架、关键配置面、常见排查方向和下一步可追问点，不一次性展开全部细节。
2. 优先用结构化表格、短清单和 Mermaid 流程图/时序图表达，少用长段文字堆叠。
3. 严禁输出任何代码片段、伪代码、命令行、JSON 示例、配置样例或可复制执行的实现内容；Mermaid 图只用于表达流程/关系，不算实现代码。
4. 即使用户要求代码或示例，也只用结构化文字描述字段、能力、约束、流程和注意事项。
5. 先判断用户关注点：配置问题关注“表/字段/取值/验证”，功能问题关注“入口流程/状态变化/关键分支/结果”。
6. 用户只问“怎么配置/是什么/怎么排查/整体流程”时，默认输出 4 到 6 条纲要；不要列出知识卡、文件路径、类名、函数名、日志短语、断言名等内部线索。
7. 如果用户问题涉及配置，必须给具体表格和字段：至少包含配置面、对应配置表/配置项、核心字段和字段用途；表名和字段名属于业务配置线索，可以保留。不要只给“基础模板/AI/技能”等概念描述。
8. 如果用户问题涉及功能，必须给 Mermaid 图解 + 结构化步骤；只说明配置作为输入从哪里影响流程，不展开配置字段明细，除非用户明确追问字段。
9. 只有用户继续追问具体字段细节、具体日志、具体错误或明确要求代码位置时，才逐步展开对应细节；仍然避免一次性倾倒所有匹配信息。
10. 如果信息不足，先说明缺口和需要的输入，不要用长篇解释填充。
"""
    if mode == "technical":
        return """\
对外回答格式（第 2 档：面向程序员解读）：
1. 同样采用渐进披露，并优先用结构化表格、短清单和 Mermaid 流程图/时序图表达，避免长段文字堆叠。
2. 先判断用户关注点：配置问题关注“表/字段/取值/验证”，功能问题关注“入口流程/状态变化/关键分支/结果”。
3. 如果用户问题涉及配置，必须先给配置明细表：配置面、对应配置表/配置项、核心字段和字段用途；再补加载链路、使用位置、默认/非法值和验证方式。
4. 如果用户问题涉及功能，必须先给 Mermaid 图解 + 结构化步骤；再补关键类、函数、调用链、数据结构、边界条件和风险点。
5. 可以引用类、函数、字段、调用链、文件路径和行号，但不要用这些细节替代整体图和结构化摘要。
6. 不直接修改代码；如需改动，只说明改动点、影响范围和验证方式。
7. 代码片段只在确有助于解释时少量引用，避免整段复制文件内容。
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
