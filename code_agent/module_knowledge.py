"""Versioned module knowledge cards.

Unlike the runtime Q&A flywheel in ``knowledge.py``, these cards are maintained
as repo files under ``docs/code-knowledge/<repo>/``. They capture stable module
maps and troubleshooting playbooks so broad questions start with domain context
instead of rediscovering the same framework every time.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

from . import config


_MAX_CARDS = 3
_MAX_CARD_CHARS = 2600


@dataclass
class Card:
    path: str
    title: str
    tags: list[str]
    body: str


def recall(query: str, *, limit: int = _MAX_CARDS) -> list[Card]:
    """Return relevant module cards for the current repo."""
    query = (query or "").strip()
    if not query:
        return []
    cards = load_cards()
    scored: list[tuple[int, Card]] = []
    for card in cards:
        score = _score(query, card)
        if score > 0:
            scored.append((score, card))
    scored.sort(key=lambda item: (-item[0], item[1].path))
    return [card for _, card in scored[:limit]]


def load_cards() -> list[Card]:
    """Load cards from common + current repo directories."""
    repo = config.current_repo().name
    roots = [
        os.path.join(config.PROJECT_ROOT, "docs", "code-knowledge", "common"),
        os.path.join(config.PROJECT_ROOT, "docs", "code-knowledge", repo),
    ]
    out: list[Card] = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            if not name.endswith(".md"):
                continue
            path = os.path.join(root, name)
            card = _read_card(path)
            if card:
                out.append(card)
    return out


def format_for_prompt(query: str) -> str:
    """Format recalled cards for system-prompt injection."""
    cards = recall(query)
    if not cards:
        return ""
    lines = [
        "已命中的模块知识卡（稳定框架/排查手册；具体结论仍需用工具核实）："
    ]
    for card in cards:
        body = card.body.strip()
        if len(body) > _MAX_CARD_CHARS:
            body = body[:_MAX_CARD_CHARS].rstrip() + "\n..."
        tag_text = f" tags={','.join(card.tags)}" if card.tags else ""
        lines.append(f"\n## {card.title}{tag_text}\n来源: {card.path}\n{body}")
    return "\n".join(lines)


def _read_card(path: str) -> Card | None:
    try:
        text = open(path, "r", encoding="utf-8").read()
    except OSError:
        return None
    title = os.path.splitext(os.path.basename(path))[0]
    tags: list[str] = []
    body = text
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            meta = text[4:end].strip()
            body = text[end + 4 :].lstrip()
            for line in meta.splitlines():
                key, _, val = line.partition(":")
                if key.strip() == "title" and val.strip():
                    title = val.strip()
                elif key.strip() == "tags":
                    tags = [t.strip() for t in re.split(r"[,，]", val) if t.strip()]
    if title == os.path.splitext(os.path.basename(path))[0]:
        m = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        if m:
            title = m.group(1).strip()
    rel = os.path.relpath(path, config.PROJECT_ROOT).replace(os.sep, "/")
    return Card(path=rel, title=title, tags=tags, body=body)


def _score(query: str, card: Card) -> int:
    q_terms = _terms(query)
    if not q_terms:
        return 0
    hay = " ".join([card.title, " ".join(card.tags), card.body]).lower()
    score = 0
    for term in q_terms:
        if term in hay:
            score += 3 if term in [t.lower() for t in card.tags] else 1
    return score


def _terms(text: str) -> list[str]:
    terms = re.findall(r"[A-Za-z_][A-Za-z0-9_]+|[一-鿿]{2,}", text)
    expanded: list[str] = []
    for term in terms:
        low = term.lower()
        expanded.append(low)
        expanded.extend(_SYNONYMS.get(low, ()))
    return list(dict.fromkeys(t for t in expanded if len(t) >= 2))


_SYNONYMS = {
    "怪物": ["monster", "enemy", "combatenemy"],
    "怪": ["monster", "enemy"],
    "敌人": ["enemy", "monster"],
    "配置": ["config", "conf", "table"],
    "技能": ["skill", "skilllistforenemy"],
    "宕机": ["crash", "error", "assert"],
    "日志": ["log", "error"],
    "monster": ["怪物", "enemy"],
    "enemy": ["怪物", "monster"],
    "skill": ["技能", "skilllistforenemy"],
    "config": ["配置", "conf", "table"],
}
