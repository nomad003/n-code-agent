"""Entry short-circuit for precise lookups (方案 2).

Some questions are pure factual lookups the symbol index can answer exactly —
"X 类定义在哪", "where is X defined", "X 在哪个文件". For those we skip the LLM
agent loop entirely and answer straight from the index: instant, free, exact.

``try_answer(question)`` returns a formatted answer string when it confidently
recognizes such a question AND the index has a unique-enough hit; otherwise it
returns None and the caller falls back to the normal agent loop. Conservative
by design: when in doubt, return None (let the LLM handle it).
"""
from __future__ import annotations

import re

from . import config

# Question patterns that ask only "where is <symbol> defined / which file".
# Each must capture the symbol name in group 1. Kept tight to avoid hijacking
# questions that actually need explanation ("X 是做什么的" must NOT match).
# All patterns are anchored to end-of-string (allowing only trailing
# filler/punctuation like 文件/里/呢/?) so compound questions such as
# "where is X defined and how does it work" do NOT short-circuit — those need
# the full agent. Trailing tail allowed: 个/一个/文件/里/中/呢/吗/。/?/？/空白.
_TAIL = r"(?:个|一个|文件|里|中|呢|吗)*\s*[?？。.]*\s*$"
_PATTERNS = [
    re.compile(r"^\s*([A-Za-z_]\w*)\s*(?:类|结构体|函数|方法)?\s*(?:的)?\s*定义\s*在\s*哪" + _TAIL, re.I),
    re.compile(r"^\s*([A-Za-z_]\w*)\s*(?:类|结构体|函数|方法)?\s*在\s*哪(?:个|一个)?\s*文件" + _TAIL, re.I),
    re.compile(r"^\s*(?:where\s+is\s+)([A-Za-z_]\w*)\s+(?:defined|declared)\s*[?？.]*\s*$", re.I),
    re.compile(r"^\s*(?:find|locate)\s+(?:the\s+)?(?:definition\s+of\s+)?([A-Za-z_]\w*)\s*$", re.I),
    re.compile(r"^\s*([A-Za-z_]\w*)\s*(?:的)?\s*(?:定义|声明)\s*(?:位置|在哪里)?\s*[?？]?\s*$", re.I),
]


def _extract_symbol(question: str) -> str | None:
    for pat in _PATTERNS:
        m = pat.match(question)
        if m:
            return m.group(1)
    return None


def try_answer(question: str) -> str | None:
    """Answer a precise "where is X defined" question from the index, or None.

    None means "not a short-circuitable question, or no index hit" → caller
    should run the normal agent loop.
    """
    if not config.USE_INDEX:
        return None
    symbol = _extract_symbol((question or "").strip())
    if not symbol:
        return None
    try:
        from . import index_query

        rows = index_query.find_symbol(symbol)
    except Exception:
        return None
    if not rows:
        return None  # index has no definition → let the LLM try (maybe a typo/macro)

    # Prefer definition-like kinds over plain references for the headline.
    defs = [r for r in rows if r["kind"] in ("class", "struct", "enum", "union", "function", "method")]
    if not defs:
        return None
    lines = [f"`{symbol}` 的定义位置（来自符号索引，未经 LLM）："]
    for r in defs[:10]:
        lines.append(f"- {r['path']}:{r['line']}  [{r['kind']}]")
    if len(defs) > 10:
        lines.append(f"- ... 另有 {len(defs) - 10} 处同名定义")
    return "\n".join(lines)
