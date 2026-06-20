"""Tests for the evaluation harness (offline — agent stubbed)."""
import json

from code_agent import config
from code_agent.evals import evaluate
import pytest


# --- scoring ---------------------------------------------------------------


def test_score_pass_all_symbols_and_file():
    r = evaluate._score(
        "SceneMgr 定义在 scene/scene_mgr.py，含 load_scene 方法",
        [],
        {"expect_symbols": ["SceneMgr", "load_scene"], "expect_files": ["scene/scene_mgr.py"]},
    )
    assert r["passed"] is True
    assert not r["missing_syms"]


def test_score_fail_missing_symbol():
    r = evaluate._score(
        "这是个场景管理器", [],
        {"expect_symbols": ["SceneMgr", "load_scene"], "expect_files": []},
    )
    assert r["passed"] is False
    assert "SceneMgr" in r["missing_syms"] and "load_scene" in r["missing_syms"]


def test_score_file_can_match_in_refs():
    # File appears only in referenced files, not the answer text → still OK.
    r = evaluate._score(
        "场景管理器，符号 SceneMgr",
        ["scene/scene_mgr.py"],
        {"expect_symbols": ["SceneMgr"], "expect_files": ["scene/scene_mgr.py"]},
    )
    assert r["passed"] is True
    assert r["file_hits"] == ["scene/scene_mgr.py"]


def test_score_no_expected_files_passes_on_symbols():
    r = evaluate._score("含 hp 字段", [], {"expect_symbols": ["hp"], "expect_files": []})
    assert r["passed"] is True


def test_score_all_files_and_phrases():
    r = evaluate._score(
        "根因是 enemy skill 配置缺失，涉及 skillcore.cpp",
        ["gameserver/tableload/skillconfig.cpp"],
        {
            "expect_all_files": [
                "gameserver/tableload/skillconfig.cpp",
                "skillcore.cpp",
            ],
            "expect_phrases": ["配置缺失", "enemy skill"],
        },
    )
    assert r["passed"] is True


def test_score_reports_missing_all_files_and_phrases():
    r = evaluate._score(
        "只提到了 skillcore.cpp",
        [],
        {
            "expect_all_files": ["skillcore.cpp", "skillconfig.cpp"],
            "expect_phrases": ["配置缺失"],
        },
    )
    assert r["passed"] is False
    assert r["missing_all_files"] == ["skillconfig.cpp"]
    assert r["missing_phrases"] == ["配置缺失"]


# --- dataset loading -------------------------------------------------------


def test_load_dataset_skips_blank_and_comments(tmp_path):
    p = tmp_path / "ds.jsonl"
    p.write_text(
        '{"question": "q1", "expect_symbols": ["A"]}\n'
        "\n"
        "# a comment\n"
        '{"question": "q2", "expect_symbols": ["B"]}\n',
        encoding="utf-8",
    )
    cases = evaluate.load_dataset(str(p))
    assert [c["question"] for c in cases] == ["q1", "q2"]


# --- evaluate() orchestration (agent stubbed) ------------------------------


@pytest.fixture
def stub_agent(monkeypatch):
    """Stub CodeAgent so evaluate() runs without an LLM."""
    answers = {}

    class FakeAgent:
        def __init__(self, *a, **k):
            self.recalled = ""

        def run(self, q):
            return answers.get(q, "")

        def _referenced_files(self):
            return []

        def _recalled_context(self, q):
            return "线索" if q in answers else ""

    monkeypatch.setattr(evaluate.agent, "CodeAgent", FakeAgent)
    return answers


def test_evaluate_pass_rate(stub_agent, tmp_path):
    stub_agent["q good"] = "包含 Foo 符号"
    stub_agent["q bad"] = "什么都没有"
    p = tmp_path / "ds.jsonl"
    p.write_text(
        json.dumps({"question": "q good", "expect_symbols": ["Foo"]}) + "\n"
        + json.dumps({"question": "q bad", "expect_symbols": ["Bar"]}) + "\n",
        encoding="utf-8",
    )
    summary = evaluate.evaluate(str(p))
    assert summary["total"] == 2 and summary["passed"] == 1
    assert summary["pass_rate"] == 0.5


def test_evaluate_twice_reports_recall(stub_agent, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "USE_KNOWLEDGE", True)
    stub_agent["q1"] = "含 Foo"
    p = tmp_path / "ds.jsonl"
    p.write_text(json.dumps({"question": "q1", "expect_symbols": ["Foo"]}) + "\n", encoding="utf-8")
    summary = evaluate.evaluate(str(p), twice=True)
    assert summary["recall_hits"] == 1 and summary["recall_rate"] == 1.0
