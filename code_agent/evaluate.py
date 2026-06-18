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
     "expect_all_files": [str, ...],  # all must appear (answer or refs)
     "expect_phrases": [str, ...],    # all must appear in the answer
     "repo": str,                     # optional CODE_REPOS name
     "mode": str,                     # optional operation mode
     "note": str}                    # optional, for humans

Usage:
    python -m code_agent.evaluate eval/dataset.sample.jsonl
    python -m code_agent.evaluate <dataset> --twice      # also measure flywheel recall
"""
from __future__ import annotations

from contextlib import contextmanager
import json
import sys

from . import agent
from . import config


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

    want_all_files = case.get("expect_all_files", [])
    all_file_hits = [f for f in want_all_files if f in haystack]
    all_files_ok = len(all_file_hits) == len(want_all_files)

    want_phrases = case.get("expect_phrases", [])
    phrase_hits = [p for p in want_phrases if p in ans]
    phrases_ok = len(phrase_hits) == len(want_phrases)

    return {
        "passed": syms_ok and files_ok and all_files_ok and phrases_ok,
        "sym_hits": sym_hits,
        "missing_syms": [s for s in want_syms if s not in ans],
        "file_hits": file_hits,
        "all_file_hits": all_file_hits,
        "missing_all_files": [f for f in want_all_files if f not in haystack],
        "phrase_hits": phrase_hits,
        "missing_phrases": [p for p in want_phrases if p not in ans],
    }


def run_case(case: dict) -> dict:
    """Run one question through a fresh CodeAgent, capturing answer + refs."""
    with config.use_repo(case.get("repo")):
        with _eval_mode(case.get("mode")):
            a = agent.CodeAgent(mode=case.get("mode") or config.AGENT_DEFAULT_MODE)
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
        miss = ""
        if not r["passed"]:
            miss = (
                f"  缺symbol={r['missing_syms']}"
                f" 缺file={r['missing_all_files']}"
                f" 缺phrase={r['missing_phrases']}"
            )
        label = case.get("id") or case["question"].splitlines()[0][:80]
        print(f"[{status}] {label}{miss}")

        if twice:
            # Ask again; with the flywheel on, the 2nd run should recall the 1st.
            with config.use_repo(case.get("repo")):
                with _eval_mode(case.get("mode")):
                    a2 = agent.CodeAgent(mode=case.get("mode") or config.AGENT_DEFAULT_MODE)
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


@contextmanager
def _eval_mode(mode: str | None):
    """Temporarily allow a dataset-requested mode for offline evaluation."""
    if not mode or mode in config.AGENT_ALLOWED_MODES:
        yield
        return
    old = config.AGENT_ALLOWED_MODES
    config.AGENT_ALLOWED_MODES = tuple(dict.fromkeys([*old, mode]))
    try:
        yield
    finally:
        config.AGENT_ALLOWED_MODES = old


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    twice = "--twice" in sys.argv
    if not args:
        print("usage: python -m code_agent.evaluate <dataset.jsonl> [--twice]")
        sys.exit(2)
    if twice and not config.USE_KNOWLEDGE:
        print("[warn] --twice 但 USE_KNOWLEDGE 未开，召回率会是 0；设 USE_KNOWLEDGE=1")
    evaluate(args[0], twice=twice)
