"""Offline evaluation for versioned code-knowledge cards.

This evaluates the markdown knowledge base itself, not an LLM answer. It checks
whether realistic questions/logs retrieve the expected cards and whether
frontmatter graph relations still point at valid cards.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
import sys
from typing import Any

from .. import config
from . import knowledge_graph


DEFAULT_TOP_K = 3


def load_dataset(path: str) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                cases.append(json.loads(line))
    return cases


def ranked_cards(query: str, *, repo: str | None = None, limit: int | None = None) -> list[dict]:
    repo_name = config.resolve_repo_name(repo)
    cards = knowledge_graph.load_cards(repo_name, include_common=True)
    scored = []
    for card in cards:
        score = knowledge_graph.score_card(query, card)
        if score > 0:
            scored.append((score, card))
    scored.sort(key=lambda item: (-item[0], item[1].id))
    if limit is not None:
        scored = scored[: max(0, limit)]
    return [
        {
            "id": card.id,
            "title": card.title,
            "path": card.path,
            "score": score,
            "type": card.type,
            "tags": card.tags,
        }
        for score, card in scored
    ]


def evaluate_case(case: dict[str, Any], *, default_top_k: int = DEFAULT_TOP_K) -> dict:
    repo = case.get("repo")
    repo_name = config.resolve_repo_name(repo)
    query = case.get("query") or case.get("question") or ""
    top_k = int(case.get("top_k") or default_top_k)
    ranked = ranked_cards(query, repo=repo, limit=max(top_k, 20))
    top = ranked[:top_k]
    top_ids = {item["id"] for item in top}
    related_ids = _related_card_ids(repo_name, top_ids)
    effective_ids = top_ids | related_ids

    expected_cards = [_card_id(item) for item in case.get("expect_cards", [])]
    missing_cards = [item for item in expected_cards if item not in effective_ids]

    any_cards = [_card_id(item) for item in case.get("expect_any_cards", [])]
    any_cards_ok = not any_cards or any(item in effective_ids for item in any_cards)

    expect_top = _card_id(case.get("expect_top_card", ""))
    top_card = top[0]["id"] if top else ""
    top_card_ok = not expect_top or top_card == expect_top

    field_failures = _check_expected_fields(case, repo=repo)
    missing_relations = _check_expected_relations(case, repo=repo)
    relation_count_failures = _check_relation_counts(case, repo=repo)

    passed = (
        not missing_cards
        and any_cards_ok
        and top_card_ok
        and not field_failures
        and not missing_relations
        and not relation_count_failures
    )
    return {
        "id": case.get("id") or query[:80],
        "repo": repo_name,
        "query": query,
        "passed": passed,
        "top_k": top_k,
        "top_cards": top,
        "related_cards": sorted(related_ids),
        "effective_cards": sorted(effective_ids),
        "missing_cards": missing_cards,
        "expect_any_cards": any_cards,
        "any_cards_ok": any_cards_ok,
        "expect_top_card": expect_top,
        "top_card": top_card,
        "top_card_ok": top_card_ok,
        "field_failures": field_failures,
        "missing_relations": missing_relations,
        "relation_count_failures": relation_count_failures,
    }


def validate_repo(repo: str | None = None) -> dict:
    repo_name = config.resolve_repo_name(repo)
    cards = knowledge_graph.load_cards(repo_name, include_common=False)
    concept_ids = {card.id for card in cards}
    graph = knowledge_graph.build_graph(repo_name)
    relation_counts = Counter(edge["relation"] for edge in graph["edges"])

    broken_links = []
    broken_relations = []
    for card in cards:
        base_dir = os.path.dirname(card.id)
        for target in knowledge_graph.markdown_links(card.body):
            resolved = os.path.normpath(os.path.join(base_dir, target)).replace(
                os.sep, "/"
            )
            if resolved not in concept_ids:
                broken_links.append(
                    {"source": card.id, "target": target, "resolved": resolved}
                )
        for relation in knowledge_graph.SEMANTIC_RELATIONS:
            for target in card.field_list(relation):
                resolved = knowledge_graph.resolve_card_ref(card.id, target, concept_ids)
                if not resolved:
                    broken_relations.append(
                        {"source": card.id, "relation": relation, "target": target}
                    )

    cards_missing_headers = []
    for card in cards:
        if card.id == "index.md":
            continue
        missing = [
            field
            for field in ("title", "type", "description", "repo", "updated_at")
            if not card.meta.get(field)
        ]
        if missing:
            cards_missing_headers.append({"card": card.id, "missing": missing})

    return {
        "repo": repo_name,
        "card_count": len(cards),
        "node_count": len(graph["nodes"]),
        "edge_count": len(graph["edges"]),
        "relation_counts": dict(sorted(relation_counts.items())),
        "broken_links": broken_links,
        "broken_relations": broken_relations,
        "cards_missing_headers": cards_missing_headers,
        "valid": not broken_links and not broken_relations and not cards_missing_headers,
    }


def evaluate(path: str, *, top_k: int = DEFAULT_TOP_K, validate: bool = True) -> dict:
    cases = load_dataset(path)
    results = [evaluate_case(case, default_top_k=top_k) for case in cases]
    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        misses = []
        if result["missing_cards"]:
            misses.append(f"缺card={result['missing_cards']}")
        if not result["any_cards_ok"]:
            misses.append(f"未命中任一卡={result['expect_any_cards']}")
        if not result["top_card_ok"]:
            misses.append(
                f"top={result['top_card']!r}, 期望={result['expect_top_card']!r}"
            )
        if result["field_failures"]:
            misses.append(f"字段失败={result['field_failures']}")
        if result["missing_relations"]:
            misses.append(f"缺关系={result['missing_relations']}")
        if result["relation_count_failures"]:
            misses.append(f"关系计数={result['relation_count_failures']}")
        detail = "  " + " ".join(misses) if misses else ""
        top = ", ".join(item["id"] for item in result["top_cards"])
        print(f"[{status}] {result['id']}  top{result['top_k']}=[{top}]{detail}")

    passed = sum(1 for item in results if item["passed"])
    repos = sorted({result["repo"] for result in results})
    if validate and not repos:
        repos = [config.resolve_repo_name(None)]
    validations = {repo: validate_repo(repo) for repo in repos} if validate else {}
    validation_ok = all(item["valid"] for item in validations.values())
    total = len(results)
    summary = {
        "total": total,
        "passed": passed,
        "pass_rate": round(passed / total, 3) if total else 0.0,
        "validation_ok": validation_ok,
        "validations": validations,
    }
    print(f"\n=== 知识召回通过 {passed}/{total} ({summary['pass_rate']:.0%}) ===")
    if validate:
        for repo, report in validations.items():
            print(
                "=== 图谱校验 "
                f"{repo}: cards={report['card_count']} nodes={report['node_count']} "
                f"edges={report['edge_count']} valid={report['valid']} ==="
            )
            if report["broken_links"]:
                print(f"broken_links={report['broken_links']}")
            if report["broken_relations"]:
                print(f"broken_relations={report['broken_relations']}")
            if report["cards_missing_headers"]:
                print(f"cards_missing_headers={report['cards_missing_headers']}")
    return summary


def _check_expected_fields(case: dict[str, Any], *, repo: str | None) -> list[dict]:
    checks = case.get("expect_fields", [])
    if not checks:
        return []
    cards = {
        card.id: card
        for card in knowledge_graph.load_cards(
            config.resolve_repo_name(repo), include_common=True
        )
    }
    failures = []
    for check in checks:
        card_id = _card_id(check.get("card", ""))
        card = cards.get(card_id)
        if not card:
            failures.append({"card": card_id, "reason": "missing_card"})
            continue
        field = check.get("field", "")
        expected = [str(item) for item in check.get("contains", [])]
        if field == "body":
            haystack = card.body
        elif field in knowledge_graph.LIST_FIELDS:
            haystack = "\n".join(card.field_list(field))
        else:
            haystack = card.meta.get(field, "")
        missing = [item for item in expected if item not in haystack]
        if missing:
            failures.append({"card": card_id, "field": field, "missing": missing})
    return failures


def _check_expected_relations(case: dict[str, Any], *, repo: str | None) -> list[dict]:
    expected = case.get("expect_relations", [])
    if not expected:
        return []
    graph = knowledge_graph.build_graph(config.resolve_repo_name(repo))
    edges = {
        (edge["source"], edge["relation"], edge["target"])
        for edge in graph["edges"]
    }
    missing = []
    for item in expected:
        source = _card_id(item.get("source", ""))
        relation = item.get("relation", "")
        target = _card_id(item.get("target", ""))
        if (source, relation, target) not in edges:
            missing.append({"source": source, "relation": relation, "target": target})
    return missing


def _check_relation_counts(case: dict[str, Any], *, repo: str | None) -> list[dict]:
    expected = case.get("expect_relation_counts", {})
    if not expected:
        return []
    graph = knowledge_graph.build_graph(config.resolve_repo_name(repo))
    counts = Counter(edge["relation"] for edge in graph["edges"])
    failures = []
    for relation, min_count in expected.items():
        actual = counts.get(relation, 0)
        if actual < int(min_count):
            failures.append(
                {"relation": relation, "actual": actual, "min": int(min_count)}
            )
    return failures


def _related_card_ids(repo: str, card_ids: set[str]) -> set[str]:
    if not card_ids:
        return set()
    graph = knowledge_graph.build_graph(repo)
    relations = set(knowledge_graph.SEMANTIC_RELATIONS) | {"links_to"}
    related = set()
    for edge in graph["edges"]:
        if edge["source"] in card_ids and edge["relation"] in relations:
            if edge["target"].endswith(".md"):
                related.add(edge["target"])
    return related


def _card_id(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = text.split("#", 1)[0].split("?", 1)[0].strip()
    text = text.replace("\\", "/")
    marker = "/docs/code-knowledge/"
    if marker in text:
        text = text.split(marker, 1)[1]
        parts = text.split("/", 1)
        text = parts[1] if len(parts) == 2 else parts[0]
    if text.startswith("docs/code-knowledge/"):
        parts = text.split("/", 3)
        text = parts[3] if len(parts) == 4 else parts[-1]
    return os.path.normpath(text).replace(os.sep, "/")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate code knowledge cards offline.")
    parser.add_argument("dataset", nargs="?", default="eval/knowledge.marvel.jsonl")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--no-validate", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)
    summary = evaluate(args.dataset, top_k=args.top_k, validate=not args.no_validate)
    if args.json_output:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["passed"] == summary["total"] and summary["validation_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
