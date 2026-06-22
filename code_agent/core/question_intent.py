"""Question-type policy for codebase Q&A.

This layer is orthogonal to operation mode:
- operation mode controls audience/style (plain/technical/edit)
- question intent controls investigation and answer structure
"""
from __future__ import annotations

import re


CLARIFY_INTENT = "clarify"
INTENTS = ("crash_stack", "outage_log", "feature_impl", "config_impl", "general")
CLASSIFIED_INTENTS = INTENTS + (CLARIFY_INTENT,)


def classify(question: str) -> str:
    """Best-effort deterministic classifier for the common user question types."""
    q = question or ""
    low = q.lower()
    if _looks_like_backtrace(q, low):
        return "crash_stack"
    if _looks_like_strong_outage_log(q, low):
        return "outage_log"
    if _needs_clarification(q, low):
        return CLARIFY_INTENT
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


def should_clarify(question: str, override: str | None = None) -> bool:
    """Return True when auto intent cannot safely pick an answer strategy."""
    return not normalize(override) and classify(question) == CLARIFY_INTENT


def clarifying_response(question: str, mode: str = "plain") -> str:
    """Deterministic response for low-information questions.

    This keeps ambiguous requests from spending a model/tool round and gives the
    user the exact missing input needed to route the next turn.
    """
    return """我还不能确定你要我按哪种方向查。请补充一个目标，任选一种：

| 方向 | 需要你补充 |
|------|------------|
| 程序 crash 堆栈 | 调用栈或 core 相关栈帧 |
| 宕机 / 错误日志 | 原始日志片段、错误短语或时间点 |
| 配置实现 | 模块 / 业务对象、配置表名或字段名 |
| 功能实现 | 功能名，以及想看流程、调用链还是数据结构 |

可以直接改成类似：“怪物技能怎么配置？”、“not find in conf 日志怎么排查？”或“Buff 添加流程怎么走？”。"""


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
    if _looks_like_strong_outage_log(q, low):
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


def _looks_like_strong_outage_log(q: str, low: str) -> bool:
    if any(s in low for s in ("assert", "check failed", "fatal", "panic")):
        return True
    if re.search(r"\b(error|warn|critical|exception)\b", low):
        return True
    if re.search(r"\b\d{2}:\d{2}:\d{2}[:.]\d{3}\b", q) and re.search(
        r"\[(error|warn|fatal|critical)\]", low
    ):
        return True
    return False


def _needs_clarification(q: str, low: str) -> bool:
    stripped = q.strip()
    if not stripped:
        return True
    if _looks_like_backtrace(q, low) or _looks_like_strong_outage_log(q, low):
        return False
    if _has_action_intent(low):
        return not _has_specific_subject(q)
    if _is_generic_request(q, low):
        return not _has_specific_subject(q)
    return _is_short_topic_only(q, low)


def _has_action_intent(low: str) -> bool:
    return any(
        s in low
        for s in (
            "怎么配置",
            "如何配置",
            "怎么配",
            "配置",
            "字段",
            "怎么实现",
            "如何实现",
            "实现逻辑",
            "流程",
            "调用链",
            "怎么查",
            "怎么排查",
            "排查",
            "分析",
            "是什么",
            "在哪",
            "哪里",
            "日志",
            "报错",
            "错误",
            "异常",
            "crash",
            "stack",
            "config",
            "feature",
            "how",
            "where",
            "what",
        )
    )


def _is_generic_request(q: str, low: str) -> bool:
    if low.strip() in {"hi", "hello", "help", "继续", "看一下", "分析一下", "怎么弄", "怎么处理"}:
        return True
    return any(
        s in low
        for s in (
            "这个问题",
            "这个怎么",
            "这里不对",
            "有问题",
            "帮我看看",
            "帮看",
        )
    )


def _has_specific_subject(q: str) -> bool:
    clean = q
    clean = re.sub(
        r"(怎么配置|如何配置|怎么配|怎么实现|如何实现|实现逻辑|怎么查|怎么排查|"
        r"配置表|配置项|配置|字段含义|字段|流程|调用链|作用|机制|是什么|在哪|哪里|"
        r"日志|报错|错误|异常|问题|怎么|如何|为什么|为何|这个|那个|这里|那里|帮我|帮忙|帮看|看一下|"
        r"分析一下|分析|排查|处理|继续|一下|请|的|了|吗|呢|吧)",
        "",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(
        r"\b(how|what|where|why|config|configuration|feature|implementation|"
        r"flow|trace|log|error|issue|problem|help|please)\b",
        "",
        clean,
        flags=re.IGNORECASE,
    )
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_:<>]*|[\u4e00-\u9fff]{2,}", clean)
    return any(token not in {"模块", "功能", "代码", "系统"} for token in tokens)


def _is_short_topic_only(q: str, low: str) -> bool:
    if _has_action_intent(low):
        return False
    compact = re.sub(r"[\s\W_]+", "", q, flags=re.UNICODE)
    if len(compact) > 12:
        return False
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_:<>]*|[\u4e00-\u9fff]{2,}", q)
    return len(tokens) <= 1


def _looks_like_config_impl(q: str, low: str) -> bool:
    if re.search(r"\b(config|configuration|cfg|ini|yaml|yml|json|toml|xml|env)\b", low):
        return True
    if re.search(
        r"\b[A-Z][A-Za-z0-9_]*(Config|Table|Limit|Follow|Statistics|Presentation)\b",
        q,
    ):
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
    CLARIFY_INTENT: "需要澄清的问题",
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
5. 不要只翻译日志文本；必须把日志反查到代码语义。
6. 最终答案必须保留关键函数名、配置表名、文件路径和原始日志短语；例如不要把 `not find in conf` 只改写成中文。""",
    "feature_impl": """\
最佳实践：
1. 先用 repo_overview() 或 glob/grep_code(files) 缩小模块范围，再用 find_symbol/grep_code(content) 定位入口。
2. 按入口 -> 核心分支 -> 下游调用 -> 数据读写/事件/消息 的顺序追踪。
3. 对跨工程问题，默认同时考虑 gameserver 和 ecs：先找调用点，再沿 include、符号名、组件类型到另一侧查定义。
4. 结论必须包含：入口、关键类/函数、主流程、关键数据结构、边界条件、扩展/修改入口。
5. 用户点名的核心模块必须列出对应文件路径；每个关键结论都尽量绑定文件路径和行号。
6. 输出结构上，必须给 Mermaid 图解、结构化步骤、参与模块、状态变化和关键分支；配置只作为输入点说明，不展开字段明细，除非用户追问配置。
7. 如果问题里出现类似 XConfig/XTable/XLimit/XFollow/Statistics/Presentation 的配置表或字段名，要同时说明配置加载文件和运行时使用文件。""",
    "config_impl": """\
最佳实践：
1. 先定位配置文件/配置表名/字段名；用 glob 找配置文件，用 grep_code(files/count) 看使用分布。
2. 追踪配置加载、解析、校验、缓存、热更/重载、默认值和错误处理。
3. 再找业务读取点，说明配置项如何影响功能流程或开关行为。
4. 结论必须包含：配置来源、字段含义、加载链路、配置加载文件、运行时使用文件、默认/非法值行为、修改后如何验证。
5. 输出结构上，必须给配置明细表格，列为：配置面、对应表/配置项、核心字段、字段用途；可配一张 Mermaid 关系图说明表之间如何协同。technical 模式再补加载文件、函数名和代码位置。
6. 如果还没确认到具体表名或字段名，必须明确标注“待核实”，并继续用工具查证；不要只输出抽象模块说明。
7. 若字段只在数据表中出现但代码未读取，要明确说明“未找到代码使用点”。""",
    "general": """\
最佳实践：
1. 先判断问题更接近 crash、日志、功能实现还是配置实现；能归类就按对应策略查。
2. 先用低成本工具缩小范围，再读关键代码片段。
3. 回答要区分已确认事实和推断；证据不足时说明还需要什么输入。""",
    CLARIFY_INTENT: """\
最佳实践：
1. 当前问题无法明确判断是 crash 堆栈、宕机日志、配置实现、功能实现还是通用代码问答。
2. 不要调用代码检索工具，不要猜测用户目标，不要输出泛泛代码概览。
3. 只追问 1 到 3 个澄清问题，并给出可选方向：crash 堆栈、宕机/错误日志、配置实现、功能实现、通用代码解释。
4. 追问必须说明每个方向需要用户补充什么输入，例如日志原文、配置表/字段、功能名或调用栈。""",
}
