"""Code knowledge graph derived from OKF-style markdown cards."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

from . import config

SEMANTIC_RELATIONS = (
    "part_of",
    "supplements",
    "contradicts",
    "supersedes",
    "depends_on",
)
LIST_FIELDS = {
    "tags",
    "symbols",
    "logs",
    "asserts",
    "question_types",
    *SEMANTIC_RELATIONS,
}

RELATIONS = [
    {
        "id": "links_to",
        "label": "内部链接",
        "short_label": "link",
        "description": (
            "一个知识卡片正文通过 Markdown 链接引用另一个知识卡片。"
        ),
        "source": "markdown_link",
    },
    {
        "id": "tagged_with",
        "label": "标签归类",
        "short_label": "tag",
        "description": "一个知识卡片在 frontmatter tags 中声明了该标签。",
        "source": "frontmatter_tags",
    },
    {
        "id": "owns_symbol",
        "label": "关键符号",
        "short_label": "symbol",
        "description": "一个知识卡片在 symbols 中声明了关键类、函数或类型。",
        "source": "frontmatter_symbols",
    },
    {
        "id": "emits_log",
        "label": "日志线索",
        "short_label": "log",
        "description": (
            "一个知识卡片在 logs 中声明了常见日志关键字或错误文本。"
        ),
        "source": "frontmatter_logs",
    },
    {
        "id": "checks_assert",
        "label": "断言线索",
        "short_label": "assert",
        "description": (
            "一个知识卡片在 asserts 中声明了常见断言、CHECK 或错误条件。"
        ),
        "source": "frontmatter_asserts",
    },
    {
        "id": "answers_question_type",
        "label": "问题类型",
        "short_label": "intent",
        "description": (
            "一个知识卡片适用于指定问题类型，例如 crash_stack、outage_log、"
            "feature_impl、config_impl。"
        ),
        "source": "frontmatter_question_types",
    },
    {
        "id": "documents_resource",
        "label": "代码资源",
        "short_label": "path",
        "description": "一个知识卡片描述了指定模块路径或代码资源。",
        "source": "frontmatter_resource",
    },
    {
        "id": "part_of",
        "label": "组成/从属",
        "short_label": "part",
        "description": (
            "A part_of B：A 是 B 的一个组成部分，例如模块属于子系统、"
            "配置链路属于框架。"
        ),
        "source": "frontmatter_relation",
    },
    {
        "id": "supplements",
        "label": "补充",
        "short_label": "plus",
        "description": "A supplements B：A 为 B 提供额外细节、示例或背景信息。",
        "source": "frontmatter_relation",
    },
    {
        "id": "contradicts",
        "label": "冲突",
        "short_label": "conflict",
        "description": "A contradicts B：A 与 B 的描述存在不一致，需要人工复核。",
        "source": "frontmatter_relation",
    },
    {
        "id": "supersedes",
        "label": "取代",
        "short_label": "newer",
        "description": (
            "A supersedes B：A 是 B 的更新版本，B 不再是最新有效信息。"
        ),
        "source": "frontmatter_relation",
    },
    {
        "id": "depends_on",
        "label": "依赖",
        "short_label": "dep",
        "description": "A depends_on B：理解 A 需要先了解 B 的内容。",
        "source": "frontmatter_relation",
    },
]


@dataclass
class KnowledgeCard:
    id: str
    path: str
    title: str
    meta: dict[str, str]
    body: str

    @property
    def type(self) -> str:
        return self.meta.get("type", "Concept")

    @property
    def description(self) -> str:
        return self.meta.get("description", "")

    @property
    def tags(self) -> list[str]:
        return meta_list(self.meta.get("tags", ""))

    def field_list(self, name: str) -> list[str]:
        return meta_list(self.meta.get(name, ""))


def repo_dir(repo: str) -> str:
    return os.path.abspath(
        os.path.join(config.PROJECT_ROOT, "docs", "code-knowledge", repo)
    )


def common_dir() -> str:
    return os.path.abspath(
        os.path.join(config.PROJECT_ROOT, "docs", "code-knowledge", "common")
    )


def load_cards(
    repo: str | None = None, *, include_common: bool = True
) -> list[KnowledgeCard]:
    """Load OKF-style markdown cards, recursively and deterministically."""
    repo_name = repo or config.current_repo().name
    roots: list[tuple[str, str]] = []
    if include_common:
        roots.append(("common", common_dir()))
    roots.append((repo_name, repo_dir(repo_name)))

    cards: list[KnowledgeCard] = []
    seen: set[str] = set()
    for _label, root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
            for filename in sorted(filenames):
                if not filename.endswith(".md"):
                    continue
                path = os.path.join(dirpath, filename)
                rel = os.path.relpath(path, root).replace(os.sep, "/")
                if rel in seen:
                    continue
                card = read_card(path, card_id=rel)
                if card:
                    cards.append(card)
                    seen.add(rel)
    return cards


def read_card(path: str, *, card_id: str | None = None) -> KnowledgeCard | None:
    try:
        text = open(path, "r", encoding="utf-8").read()
    except OSError:
        return None
    meta, body = frontmatter(text)
    title = meta.get("title") or os.path.splitext(os.path.basename(path))[0]
    if title == os.path.splitext(os.path.basename(path))[0]:
        m = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        if m:
            title = m.group(1).strip()
    rel = os.path.relpath(path, config.PROJECT_ROOT).replace(os.sep, "/")
    return KnowledgeCard(
        id=(card_id or os.path.basename(path)).replace(os.sep, "/"),
        path=rel,
        title=title,
        meta=meta,
        body=body,
    )


def frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    raw = text[4:end].strip()
    body = text[end + 4 :].lstrip()
    meta: dict[str, str] = {}
    for line in raw.splitlines():
        key, sep, val = line.partition(":")
        if sep and key.strip():
            meta[key.strip()] = val.strip().strip('"')
    return meta, body


def meta_list(value: str) -> list[str]:
    raw = (value or "").strip().strip("[]")
    return [
        item.strip().strip("'\"")
        for item in re.split(r"[,，]", raw)
        if item.strip()
    ]


def markdown_links(markdown: str) -> list[str]:
    out: list[str] = []
    for href in re.findall(r"\[[^\]]+\]\(([^)]+)\)", markdown or ""):
        if href.startswith(("http://", "https://", "#", "mailto:")):
            continue
        target = href.split("#", 1)[0].split("?", 1)[0].strip()
        if not target or not target.endswith(".md"):
            continue
        out.append(os.path.normpath(target).replace(os.sep, "/"))
    return list(dict.fromkeys(out))


def build_graph(repo: str | None = None) -> dict:
    """Build frontend graph data for a repo knowledge bundle."""
    repo_name = repo or config.current_repo().name
    cards = load_cards(repo_name, include_common=False)
    nodes: list[dict] = []
    edges: list[dict] = []
    concept_ids = {card.id for card in cards}
    node_ids: set[str] = set()
    edge_ids: set[str] = set()

    def add_node(node: dict) -> None:
        if node["id"] in node_ids:
            return
        node_ids.add(node["id"])
        nodes.append(node)

    def add_edge(source: str, target: str, relation: str) -> None:
        edge_id = f"{source}->{relation}->{target}"
        if edge_id in edge_ids:
            return
        edge_ids.add(edge_id)
        edges.append(
            {
                "id": edge_id,
                "source": source,
                "target": target,
                "relation": relation,
            }
        )

    for card in cards:
        add_node(
            {
                "id": card.id,
                "kind": "concept",
                "title": card.title,
                "type": card.type,
                "description": card.description,
                "resource": card.meta.get("resource", ""),
                "tags": card.tags,
                "path": card.path,
            }
        )

    for card in cards:
        for tag in card.tags:
            node_id = f"tag:{tag}"
            add_node({"id": node_id, "kind": "tag", "title": tag, "type": "Tag"})
            add_edge(card.id, node_id, "tagged_with")
        for symbol in card.field_list("symbols"):
            node_id = f"symbol:{symbol}"
            add_node({"id": node_id, "kind": "symbol", "title": symbol, "type": "Symbol"})
            add_edge(card.id, node_id, "owns_symbol")
        for log in card.field_list("logs"):
            node_id = f"log:{log}"
            add_node({"id": node_id, "kind": "log", "title": log, "type": "Log"})
            add_edge(card.id, node_id, "emits_log")
        for item in card.field_list("asserts"):
            node_id = f"assert:{item}"
            add_node({"id": node_id, "kind": "assert", "title": item, "type": "Assert"})
            add_edge(card.id, node_id, "checks_assert")
        for qtype in card.field_list("question_types"):
            node_id = f"question_type:{qtype}"
            add_node(
                {
                    "id": node_id,
                    "kind": "question_type",
                    "title": qtype,
                    "type": "Question Type",
                }
            )
            add_edge(card.id, node_id, "answers_question_type")
        resource = card.meta.get("resource", "").strip()
        if resource:
            node_id = f"resource:{resource}"
            add_node(
                {
                    "id": node_id,
                    "kind": "resource",
                    "title": resource,
                    "type": "Resource",
                }
            )
            add_edge(card.id, node_id, "documents_resource")

        base_dir = os.path.dirname(card.id)
        for target in markdown_links(card.body):
            resolved = os.path.normpath(os.path.join(base_dir, target)).replace(
                os.sep, "/"
            )
            if resolved in concept_ids:
                add_edge(card.id, resolved, "links_to")
        for relation in SEMANTIC_RELATIONS:
            for target in card.field_list(relation):
                resolved = resolve_card_ref(card.id, target, concept_ids)
                if resolved:
                    add_edge(card.id, resolved, relation)

    return {"repo": repo_name, "nodes": nodes, "edges": edges, "relations": RELATIONS}


def resolve_card_ref(source_id: str, ref: str, concept_ids: set[str]) -> str | None:
    """Resolve a frontmatter relation target to a card id."""
    target = (ref or "").strip().strip("`'\"")
    if not target:
        return None
    link_match = re.search(r"\[[^\]]+\]\(([^)]+)\)", target)
    if link_match:
        target = link_match.group(1)
    target = target.split("#", 1)[0].split("?", 1)[0].strip()
    if not target:
        return None
    if not target.endswith(".md"):
        target += ".md"
    candidates = [
        os.path.normpath(target).replace(os.sep, "/"),
        os.path.normpath(os.path.join(os.path.dirname(source_id), target)).replace(
            os.sep, "/"
        ),
    ]
    for candidate in candidates:
        if candidate in concept_ids:
            return candidate
    basename = os.path.basename(target)
    matches = sorted(
        card_id for card_id in concept_ids if os.path.basename(card_id) == basename
    )
    if len(matches) == 1:
        return matches[0]
    return None


def format_map_for_prompt(query: str, *, limit: int = 12) -> str:
    """Return a compact code knowledge map for system prompt injection."""
    cards = load_cards(include_common=True)
    if not cards:
        return ""
    scored = [(score_card(query, card), card) for card in cards]
    scored.sort(key=lambda item: (-item[0], item[1].id))
    selected = [card for score, card in scored if score > 0][:limit]
    if len(selected) < min(limit, len(cards)):
        picked = {card.id for card in selected}
        selected.extend(card for _score, card in scored if card.id not in picked)
        selected = selected[: min(limit, len(cards))]

    lines = [
        "代码知识库地图（稳定导航；结论必须继续用工具核实）：",
        (
            "优先按 title/resource/symbols/logs/asserts/question_types 定位卡片；"
            "search/grep 只用于核实当前代码。"
        ),
    ]
    for card in selected:
        parts = []
        if card.description:
            parts.append(card.description)
        resource = card.meta.get("resource", "")
        if resource:
            parts.append(f"resource={resource}")
        for field in (
            "symbols",
            "logs",
            "asserts",
            "question_types",
            *SEMANTIC_RELATIONS,
        ):
            vals = card.field_list(field)
            if vals:
                parts.append(f"{field}={', '.join(vals[:5])}")
        lines.append(f"- {card.id}: {card.title} ({card.type})；" + "；".join(parts))
    return "\n".join(lines)


def score_card(query: str, card: KnowledgeCard) -> int:
    terms = terms_for_query(query)
    if not terms:
        return 0
    is_reference = is_reference_card(card)
    hay_parts = [
        card.id,
        card.title,
        card.type,
        card.description,
    ]
    if not is_reference:
        hay_parts.append(card.body)
    for key in (
        "tags",
        "resource",
        "module",
    ):
        hay_parts.append(card.meta.get(key, ""))
    if not is_reference:
        for key in (
            "symbols",
            "logs",
            "asserts",
            "question_types",
            *SEMANTIC_RELATIONS,
        ):
            hay_parts.append(card.meta.get(key, ""))
    hay = " ".join(hay_parts).lower()
    score = 0
    tag_values = {
        item.lower()
        for key in LIST_FIELDS
        for item in meta_list(card.meta.get(key, ""))
    }
    for term in terms:
        if term in hay:
            score += 3 if term in tag_values else 1
    if score and is_reference and is_broad_knowledge_query(query):
        score += 2
    if score:
        score = max(0, score - reference_card_penalty(query, card))
    return score


def reference_card_penalty(query: str, card: KnowledgeCard) -> int:
    """Prefer concrete module cards unless the user asks for a map/overview."""
    if not is_reference_card(card):
        return 0
    if is_broad_knowledge_query(query):
        return 0
    return 24


def is_broad_knowledge_query(query: str) -> bool:
    text = (query or "").lower()
    broad_hints = (
        "总体",
        "框架",
        "概览",
        "索引",
        "目录",
        "模块",
        "有哪些",
        "架构",
        "地图",
        "层",
        "overview",
        "framework",
        "architecture",
        "module",
        "modules",
        "index",
        "map",
    )
    return any(hint in text for hint in broad_hints)


def is_reference_card(card: KnowledgeCard) -> bool:
    return (
        card.type.lower() == "reference"
        or card.id == "index.md"
        or card.id.endswith("/index.md")
    )


def terms_for_query(text: str) -> list[str]:
    terms = re.findall(r"[A-Za-z_][A-Za-z0-9_:.-]+|[一-鿿]{2,}", text or "")
    expanded: list[str] = []
    for term in terms:
        low = term.lower()
        expanded.append(low)
        if re.fullmatch(r"[一-鿿]{3,}", term):
            for size in (2, 3, 4):
                for i in range(0, len(term) - size + 1):
                    expanded.append(term[i : i + size])
        expanded.extend(SYNONYMS.get(low, ()))
    return list(dict.fromkeys(t for t in expanded if len(t) >= 2))


SYNONYMS = {
    "怪物": ["monster", "enemy", "combatenemy"],
    "怪": ["monster", "enemy"],
    "敌人": ["enemy", "monster"],
    "配置": ["config", "conf", "table"],
    "表": ["table", "config", "conf"],
    "技能": ["skill", "skilllistforenemy"],
    "宕机": ["crash", "error", "assert", "outage_log"],
    "崩溃": ["crash", "backtrace", "crash_stack"],
    "日志": ["log", "error", "outage_log"],
    "断言": ["assert", "check", "CHECK_COND"],
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
