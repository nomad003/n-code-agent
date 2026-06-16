"""Q&A evaluation harness (roadmap 方向 E + 方案 3 hit-rate validation).

Runs a dataset of {question → expected files/symbols} through the agent and
scores each answer. Two uses:

1. Regression / tuning yardstick: quantify how "换模型 / 改 prompt / 调限额"
   move quality, so changes aren't blind.
2. 方案 3 flywheel hit-rate: with --twice, each question is asked twice (the
   first precipitates knowledge, the second should recall it); we report how
   often the 2nd run recalled the 1st — the signal for whether to enable the
   flywheel by default.

A case "passes" when the answer mentions every expected symbol AND (if given)
at least one expected file path. Scoring is substring-based — deliberately
simple and deterministic, no LLM judge.

Dataset format: JSONL, one object per line:
    {"question": str,
     "expect_symbols": [str, ...],   # all must appear in the answer
     "expect_files":   [str, ...],   # at least one must appear (answer or refs)
     "note": str}                    # optional, for humans

Usage:
    python evaluate.py eval/dataset.sample.jsonl
    python evaluate.py <dataset> --twice      # also measure flywheel recall
"""
from __future__ import annotations

import json
import sys

import agent
import config


def load_dataset(path: str) -> list[dict]:
    cases = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                cases.append(json.loads(line))
    return cases


def _score(answer: str, refs: list[str], case: dict) -> dict:
    """Score one answer against a case's expectations."""
    ans = answer or ""
    haystack = ans + "\n" + "\n".join(refs)

    want_syms = case.get("expect_symbols", [])
    sym_hits = [s for s in want_syms if s in ans]
    syms_ok = len(sym_hits) == len(want_syms)

    want_files = case.get("expect_files", [])
    file_hits = [f for f in want_files if f in haystack]
    files_ok = (not want_files) or bool(file_hits)

    return {
        "passed": syms_ok and files_ok,
        "sym_hits": sym_hits,
        "missing_syms": [s for s in want_syms if s not in ans],
        "file_hits": file_hits,
    }


def run_case(case: dict) -> dict:
    """Run one question through a fresh CodeAgent, capturing answer + refs."""
    a = agent.CodeAgent()
    answer = a.run(case["question"])
    refs = a._referenced_files()
    result = _score(answer, refs, case)
    result.update({"question": case["question"], "answer": answer, "refs": refs})
    return result


def evaluate(path: str, *, twice: bool = False) -> dict:
    cases = load_dataset(path)
    results = []
    recalled = 0
    for case in cases:
        r = run_case(case)
        results.append(r)
        status = "PASS" if r["passed"] else "FAIL"
        miss = "" if r["passed"] else f"  缺symbol={r['missing_syms']}"
        print(f"[{status}] {case['question']}{miss}")

        if twice:
            # Ask again; with the flywheel on, the 2nd run should recall the 1st.
            a2 = agent.CodeAgent()
            a2.recalled = a2._recalled_context(case["question"])
            if a2.recalled:
                recalled += 1
            a2.run(case["question"])

    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    summary = {
        "total": total,
        "passed": passed,
        "pass_rate": round(passed / total, 3) if total else 0.0,
    }
    if twice:
        summary["recall_hits"] = recalled
        summary["recall_rate"] = round(recalled / total, 3) if total else 0.0
    print(f"\n=== 通过 {passed}/{total} ({summary['pass_rate']:.0%}) ===")
    if twice:
        print(f"=== 飞轮召回 {recalled}/{total} ({summary['recall_rate']:.0%}) ===")
    return summary


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    twice = "--twice" in sys.argv
    if not args:
        print("usage: python evaluate.py <dataset.jsonl> [--twice]")
        sys.exit(2)
    if twice and not config.USE_KNOWLEDGE:
        print("[warn] --twice 但 USE_KNOWLEDGE 未开，召回率会是 0；设 USE_KNOWLEDGE=1")
    evaluate(args[0], twice=twice)
