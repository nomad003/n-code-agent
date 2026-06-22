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

_FENCED_BLOCK_RE = re.compile(r"```([^\n`]*)\n([\s\S]*?)```")
_ALLOWED_FENCED_LANGS = {"mermaid"}
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
_INTERNAL_EVIDENCE_HEADING_RE = re.compile(r"^\s*#{0,3}\s*关键线索\s*$")
# Any CJK character on a line marks it as natural-language prose — keep it even
# if it superficially looks like a config/code line (e.g. "- host: 主机地址"
# from a structured field description).
_CJK_RE = re.compile(r"[一-鿿]")


def contains_forbidden_content(text: str) -> bool:
    """Return True when text contains code, commands, or config examples."""
    if not text:
        return False
    for match in _FENCED_BLOCK_RE.finditer(text):
        if not _is_allowed_fenced_block(match):
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
        if _is_allowed_fenced_block(_match):
            return _match.group(0)
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
    cleaned = _strip_internal_evidence(cleaned)
    cleaned = _dedupe_repeated_blocks(cleaned)
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


def _is_allowed_fenced_block(match: re.Match) -> bool:
    lang = (match.group(1) or "").strip().lower().split()
    return bool(lang and lang[0] in _ALLOWED_FENCED_LANGS)


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


def _strip_internal_evidence(text: str) -> str:
    """Remove internal evidence footers from plain-mode answers.

    The agent may use knowledge cards, file paths, symbols, logs and asserts as
    evidence. Plain users should get a progressive overview first, not the raw
    retrieval/debug footer.
    """
    if not text:
        return text
    out: list[str] = []
    skipping = False
    for line in text.splitlines():
        stripped = line.strip()
        if _INTERNAL_EVIDENCE_HEADING_RE.match(stripped):
            skipping = True
            continue
        if skipping and stripped.startswith("#") and "关键线索" not in stripped:
            skipping = False
        if skipping:
            continue
        if re.match(r"^\s*-\s*(知识卡|关键文件|关键符号|日志短语|断言)\s*[:：]", line):
            continue
        out.append(line)
    return _collapse_blank_lines("\n".join(out)).strip()


def _dedupe_repeated_blocks(text: str) -> str:
    """Drop repeated markdown/prose blocks from plain answers.

    Some models repeat the same outline twice with tiny formatting differences
    after inline-code stripping. Block-level dedupe is conservative enough for
    plain summaries and avoids shipping duplicated sections to users.
    """
    blocks = re.split(r"\n\s*\n", text.strip())
    seen: set[str] = set()
    out: list[str] = []
    for block in blocks:
        norm = re.sub(r"\s+", " ", block.strip())
        norm = norm.replace("**", "").replace("__", "")
        if len(norm) >= 12 and norm in seen:
            continue
        if norm:
            seen.add(norm)
        out.append(block.strip())
    return _collapse_blank_lines("\n\n".join(part for part in out if part)).strip()
