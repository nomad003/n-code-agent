"""Versioned module knowledge cards.

Unlike the runtime Q&A flywheel in ``knowledge.py``, these cards are maintained
as repo files under ``docs/code-knowledge/<repo>/``. They capture stable module
maps and troubleshooting playbooks so broad questions start with domain context
instead of rediscovering the same framework every time.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import config
from . import knowledge_graph


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
    cards = knowledge_graph.load_cards(config.current_repo().name, include_common=True)
    scored: list[tuple[int, knowledge_graph.KnowledgeCard]] = []
    for card in cards:
        score = knowledge_graph.score_card(query, card)
        if score > 0:
            scored.append((score, card))
    scored.sort(key=lambda item: (-item[0], item[1].path))
    return [_to_card(card) for _, card in scored[:limit]]


def load_cards() -> list[Card]:
    """Load cards from common + current repo directories."""
    return [
        _to_card(card)
        for card in knowledge_graph.load_cards(
            config.current_repo().name, include_common=True
        )
    ]


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
    card = knowledge_graph.read_card(path)
    if not card:
        return None
    return _to_card(card)


def _to_card(card: knowledge_graph.KnowledgeCard) -> Card:
    return Card(path=card.path, title=card.title, tags=card.tags, body=card.body)


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
    return knowledge_graph.terms_for_query(text)


_SYNONYMS = {
    "怪物": ["monster", "enemy", "combatenemy"],
    "怪": ["monster", "enemy"],
    "敌人": ["enemy", "monster"],
    "配置": ["config", "conf", "table"],
    "表": ["table", "config", "conf"],
    "技能": ["skill", "skilllistforenemy"],
    "宕机": ["crash", "error", "assert"],
    "日志": ["log", "error"],
    "场景": ["scene", "scenemgr"],
    "关卡": ["level", "spawner"],
    "战斗": ["combat", "battle"],
    "单位": ["unit", "combatunit"],
    "角色": ["role", "combatrole"],
    "buff": ["xbuff", "增益"],
    "ai": ["agent", "node", "skill"],
    "ecs": ["xecs", "component", "system"],
    "monster": ["怪物", "enemy"],
    "enemy": ["怪物", "monster"],
    "skill": ["技能", "skilllistforenemy"],
    "config": ["配置", "conf", "table"],
    "scene": ["场景", "scenemgr"],
    "level": ["关卡", "spawner"],
    "combat": ["战斗", "battle"],
    "unit": ["单位", "combatunit"],
    "role": ["角色", "combatrole"],
    "xecs": ["ecs", "component", "system"],
}
