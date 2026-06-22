"""Maintained common Q&A cards.

These are curated Markdown answers under ``docs/code-knowledge/<repo>/common-qa``.
They are different from runtime Q&A history: a common QA card is reviewed,
versioned and safe to return directly when the user question matches one of its
declared aliases.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .. import config
from . import knowledge_graph


QA_DIR_PREFIX = "common-qa/"


@dataclass
class CommonQA:
    path: str
    title: str
    questions: list[str]
    aliases: list[str]
    tags: list[str]
    body: str

    @property
    def prompts(self) -> list[str]:
        return list(dict.fromkeys([*self.questions, *self.aliases]))


def load(repo: str | None = None, *, include_common: bool = True) -> list[CommonQA]:
    """Load curated common QA cards for a repo."""
    repo_name = repo or config.current_repo().name
    cards = knowledge_graph.load_cards(repo_name, include_common=include_common)
    out: list[CommonQA] = []
    for card in cards:
        if not _is_common_qa(card):
            continue
        out.append(
            CommonQA(
                path=card.id,
                title=card.title,
                questions=card.field_list("questions"),
                aliases=card.field_list("aliases"),
                tags=card.tags,
                body=card.body.strip(),
            )
        )
    return out


def find_match(query: str, *, repo: str | None = None) -> CommonQA | None:
    """Return a high-confidence maintained answer for a user query."""
    query_key = _normalize_query(query)
    if not query_key:
        return None
    candidates: list[tuple[int, CommonQA]] = []
    for item in load(repo):
        score = _score(query_key, item)
        if score >= 90:
            candidates.append((score, item))
    if not candidates:
        return None
    candidates.sort(key=lambda pair: (-pair[0], pair[1].path))
    return candidates[0][1]


def answer_if_match(query: str, *, repo: str | None = None) -> str | None:
    item = find_match(query, repo=repo)
    if not item:
        return None
    return item.body


def llm_candidates(query: str, *, repo: str | None = None, limit: int = 8) -> list[CommonQA]:
    """Return plausible candidates for LLM intent routing.

    This is deliberately broader than ``find_match``: it only decides whether a
    card is worth showing to the LLM router, not whether it is safe to return.
    """
    terms = knowledge_graph.terms_for_query(query)
    if not terms:
        return []
    scored: list[tuple[int, CommonQA]] = []
    for item in load(repo):
        hay = " ".join(
            [item.path, item.title, *item.questions, *item.aliases, *item.tags]
        ).lower()
        score = sum(1 for term in terms if term in hay)
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda pair: (-pair[0], pair[1].path))
    return [item for _score, item in scored[:limit]]


def _is_common_qa(card: knowledge_graph.KnowledgeCard) -> bool:
    card_type = card.type.strip().lower()
    return card.id.startswith(QA_DIR_PREFIX) or card_type in {
        "common qa",
        "common q&a",
        "faq",
        "code qa",
    }


def _score(query_key: str, item: CommonQA) -> int:
    best = 0
    for prompt in item.prompts:
        prompt_key = _normalize_query(prompt)
        if not prompt_key:
            continue
        if query_key == prompt_key:
            best = max(best, 120)
        elif len(prompt_key) >= 4 and prompt_key in query_key:
            best = max(best, 105)
        elif len(query_key) >= 4 and query_key in prompt_key:
            best = max(best, 95)
    return best


def _normalize_query(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(
        r"(怎么|如何|怎样|请问|一下|详细|介绍|说明|讲讲|看看|"
        r"what|how|where|please)",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return re.sub(r"[\s\W_]+", "", text, flags=re.UNICODE)
