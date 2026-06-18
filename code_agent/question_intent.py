"""Question-type policy for codebase Q&A.

This layer is orthogonal to operation mode:
- operation mode controls audience/style (plain/technical/edit)
- question intent controls investigation and answer structure
"""
from __future__ import annotations

import re


INTENTS = ("crash_stack", "outage_log", "feature_impl", "config_impl", "general")


def classify(question: str) -> str:
    """Best-effort deterministic classifier for the common user question types."""
    q = question or ""
    low = q.lower()
    if _looks_like_backtrace(q, low):
        return "crash_stack"
    if _looks_like_outage_log(q, low):
        return "outage_log"
    if _looks_like_config_impl(q, low):
        return "config_impl"
    if _looks_like_feature_impl(q, low):
        return "feature_impl"
    return "general"


def prompt(question: str, override: str | None = None) -> str:
    """Prompt addendum for the classified question type."""
    intent = normalize(override) if override else classify(question)
    rules = _PROMPTS.get(intent, _PROMPTS["general"])
    return f"当前问题类型：{_LABELS[intent]}\n\n{rules}"


def normalize(intent: str | None) -> str:
    """Normalize an explicit question type from API/UI callers."""
    key = (intent or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "crash": "crash_stack",
        "stack": "crash_stack",
        "backtrace": "crash_stack",
        "crash_stack": "crash_stack",
        "log": "outage_log",
        "outage": "outage_log",
        "error_log": "outage_log",
        "outage_log": "outage_log",
        "feature": "feature_impl",
        "implementation": "feature_impl",
        "feature_impl": "feature_impl",
        "config": "config_impl",
        "configuration": "config_impl",
        "config_impl": "config_impl",
        "general": "general",
        "auto": "",
        "": "",
    }
    normalized = aliases.get(key)
    if normalized is None:
        raise ValueError(
            f"unknown question_type {intent!r}; expected one of: auto, "
            + ", ".join(INTENTS)
        )
    return normalized


def _looks_like_backtrace(q: str, low: str) -> bool:
    if re.search(r"(?m)^\s*#\d+\s+", q):
        return True
    return any(
        s in low
        for s in (
            "backtrace",
            "stack trace",
            "call stack",
            "core dump",
            "coredump",
            "sigsegv",
            "segmentation fault",
            "崩溃栈",
            "调用栈",
            "堆栈",
            "栈帧",
            "core文件",
            "core 文件",
        )
    )


def _looks_like_outage_log(q: str, low: str) -> bool:
    if any(s in low for s in ("assert", "check failed", "fatal", "panic")):
        return True
    if re.search(r"\b(error|warn|critical|exception)\b", low):
        return True
    return any(
        s in low
        for s in (
            "宕机",
            "挂了",
            "进程退出",
            "服务退出",
            "错误日志",
            "报错日志",
            "异常日志",
            "断言",
            "日志",
        )
    )


def _looks_like_config_impl(q: str, low: str) -> bool:
    if re.search(r"\b(config|configuration|cfg|ini|yaml|yml|json|toml|xml|env)\b", low):
        return True
    return any(
        s in low
        for s in (
            "配置",
            "配置表",
            "配置项",
            "配置文件",
            "字段含义",
            "字段怎么",
            "读表",
            "加载表",
            "热更",
            "开关",
        )
    )


def _looks_like_feature_impl(q: str, low: str) -> bool:
    return any(
        s in low
        for s in (
            "怎么实现",
            "如何实现",
            "实现逻辑",
            "实现流程",
            "功能实现",
            "流程",
            "调用链",
            "做什么",
            "作用",
            "机制",
            "feature",
            "implementation",
            "how does",
            "how is",
        )
    )


_LABELS = {
    "crash_stack": "程序 crash 堆栈分析",
    "outage_log": "宕机/错误日志分析",
    "feature_impl": "功能实现分析",
    "config_impl": "配置实现分析",
    "general": "通用代码问答",
}


_PROMPTS = {
    "crash_stack": """\
最佳实践：
1. 先定位栈顶第一个业务帧；若用户贴的是原始 backtrace，优先使用 resolve_frame(frame) 映射每个关键栈帧。
2. 若栈帧自带 file:line，直接 read_file 读取该行前后上下文；否则用 resolve_frame 的候选位置读代码。
3. 结合上一帧/下一帧判断调用关系，避免只看单行就下结论。
4. 结论必须包含：最可能崩溃点、触发条件、证据位置、为什么会到这里、下一步排查/修复建议。
5. 如果是空指针、越界、use-after-free、断言失败、竞态或配置数据异常，要明确说出判断依据；证据不足时标注不确定。""",
    "outage_log": """\
最佳实践：
1. 如果日志像 ASSERT/CHECK/断言失败，先调用 find_assert_context(message)；拿到断言语句和上下文后再继续追踪。
2. 普通日志先调用 find_log_source(message) 定位打印点；必要时再 grep_code 搜固定片段或错误码。
3. 读取打印点附近代码，沿错误分支、返回码、上游调用、配置/数据来源继续追踪。
4. 结论必须包含：日志含义、触发条件、代码位置、可能影响范围、排查顺序和需要补充的运行时信息。
5. 不要只翻译日志文本；必须把日志反查到代码语义。""",
    "feature_impl": """\
最佳实践：
1. 先用 repo_overview() 或 glob/grep_code(files) 缩小模块范围，再用 find_symbol/grep_code(content) 定位入口。
2. 按入口 -> 核心分支 -> 下游调用 -> 数据读写/事件/消息 的顺序追踪。
3. 对跨工程问题，默认同时考虑 gameserver 和 ecs：先找调用点，再沿 include、符号名、组件类型到另一侧查定义。
4. 结论必须包含：入口、关键类/函数、主流程、关键数据结构、边界条件、扩展/修改入口。
5. 不要泛泛描述模块；每个关键结论都尽量绑定文件路径和行号。""",
    "config_impl": """\
最佳实践：
1. 先定位配置文件/配置表名/字段名；用 glob 找配置文件，用 grep_code(files/count) 看使用分布。
2. 追踪配置加载、解析、校验、缓存、热更/重载、默认值和错误处理。
3. 再找业务读取点，说明配置项如何影响功能流程或开关行为。
4. 结论必须包含：配置来源、字段含义、加载链路、使用位置、默认/非法值行为、修改后如何验证。
5. 若字段只在数据表中出现但代码未读取，要明确说明“未找到代码使用点”。""",
    "general": """\
最佳实践：
1. 先判断问题更接近 crash、日志、功能实现还是配置实现；能归类就按对应策略查。
2. 先用低成本工具缩小范围，再读关键代码片段。
3. 回答要区分已确认事实和推断；证据不足时说明还需要什么输入。""",
}
