"""Deterministic output policy for external agent answers.

The model is instructed to avoid implementation content, but prompt rules are
not enforcement. This module is the programmatic guardrail applied at service
boundaries: it removes code/config/command examples and leaves a concise marker
so callers know content was intentionally withheld.
"""
from __future__ import annotations

import re

from . import operation_modes


_NOTICE = "（已按输出策略省略实现内容，仅保留结构化描述。）"

_FENCED_BLOCK_RE = re.compile(r"```[\s\S]*?```")
_INLINE_CODE_RE = re.compile(r"`([^`\n]{1,200})`")
_JSON_KEY_RE = re.compile(r'^\s*"[^"]+"\s*:\s*')
_YAML_CONFIG_RE = re.compile(
    r"^\s*(?:mcpServers|type|url|command|args|env|model|provider|api[_-]?key|"
    r"base[_-]?url|host|port|path)\s*:\s*\S",
    re.IGNORECASE,
)
_ENV_ASSIGN_RE = re.compile(r"^\s*[A-Z][A-Z0-9_]{2,}\s*=\s*\S+")
_SHELL_RE = re.compile(
    r"^\s*(?:\$|#)?\s*(?:curl|python3?|pip|npm|pnpm|yarn|git|cd|export|"
    r"uvicorn|pytest|docker|kubectl|make|bash|sh)\b"
)
_CODE_RE = re.compile(
    r"^\s*(?:def|class|function|func|import|from|#include|using\s+namespace|"
    r"public:|private:|protected:|return\b|if\s*\(|for\s*\(|while\s*\(|"
    r"try:|except\b|const\s+|let\s+|var\s+)\b"
)
# Any CJK character on a line marks it as natural-language prose — keep it even
# if it superficially looks like a config/code line (e.g. "- host: 主机地址"
# from a structured field description).
_CJK_RE = re.compile(r"[一-鿿]")


def contains_forbidden_content(text: str) -> bool:
    """Return True when text contains code, commands, or config examples."""
    if not text:
        return False
    if _FENCED_BLOCK_RE.search(text):
        return True
    for line in text.splitlines():
        if _is_forbidden_line(line):
            return True
    return False


def enforce(text: str, mode: str = "plain") -> str:
    """Strip forbidden implementation content from an external answer.

    This is intentionally conservative and deterministic. It does not try to
    preserve executable snippets in any form; callers asking for code still get
    only structural description.
    """
    if not text:
        return text
    if operation_modes.normalize(mode) != "plain":
        return text

    changed = False

    def _block_repl(_match: re.Match) -> str:
        nonlocal changed
        changed = True
        return _NOTICE

    text = _FENCED_BLOCK_RE.sub(_block_repl, text)
    text = _INLINE_CODE_RE.sub(r"\1", text)

    out: list[str] = []
    notice_pending = False
    for line in text.splitlines():
        if _is_forbidden_line(line):
            changed = True
            if not notice_pending:
                out.append(_NOTICE)
                notice_pending = True
            continue
        out.append(line)
        if line.strip():
            notice_pending = False

    cleaned = _collapse_blank_lines("\n".join(out)).strip()
    if changed and cleaned and _NOTICE not in cleaned:
        cleaned = f"{cleaned}\n{_NOTICE}"
    if changed and not cleaned:
        return _NOTICE
    return cleaned


def _is_forbidden_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped in ("{", "}", "[", "]"):
        return True
    # Prose that happens to start with an English keyword (`return 字段...`) or
    # describes a field (`- host: 主机地址`) must survive. Real code/config
    # samples don't mix CJK into identifiers/values, so any CJK on the line is
    # a strong signal it's prose, not implementation content.
    if _CJK_RE.search(line):
        return False
    return any(
        pattern.search(line)
        for pattern in (
            _JSON_KEY_RE,
            _YAML_CONFIG_RE,
            _ENV_ASSIGN_RE,
            _SHELL_RE,
            _CODE_RE,
        )
    )


def _collapse_blank_lines(text: str) -> str:
    lines: list[str] = []
    blank = False
    for line in text.splitlines():
        is_blank = not line.strip()
        if is_blank and blank:
            continue
        lines.append(line.rstrip())
        blank = is_blank
    return "\n".join(lines)
