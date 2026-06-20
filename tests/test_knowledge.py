"""Tests for the knowledge flywheel (方案 3): store, recall, staleness."""
from code_agent import config
from code_agent.kb import knowledge
import pytest


@pytest.fixture
def kb(tmp_path, monkeypatch):
    """Isolated knowledge DB + a temp target codebase to hash refs against."""
    root = tmp_path / "src"
    root.mkdir()
    (root / "scene.cpp").write_text("// SceneMgr impl v1\n", encoding="utf-8")
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(root))
    monkeypatch.setattr(config, "KNOWLEDGE_DB_PATH", str(tmp_path / "kb.db"))
    monkeypatch.setattr(config, "USE_KNOWLEDGE", True)
    return root


# --- store / recall --------------------------------------------------------


def test_store_and_recall(kb):
    rid = knowledge.store("SceneMgr 是做什么的？", "场景管理器", ["scene.cpp"])
    assert rid is not None
    hits = knowledge.recall("SceneMgr")
    assert len(hits) == 1
    assert hits[0]["answer"] == "场景管理器"
    assert hits[0]["refs"] == ["scene.cpp"]
    assert hits[0]["stale"] is False


def test_store_rejects_empty(kb):
    assert knowledge.store("", "ans", []) is None
    assert knowledge.store("q", "", []) is None


def test_recall_no_match(kb):
    knowledge.store("foo question", "bar", [])
    assert knowledge.recall("completely unrelated xyz") == []


def test_recall_without_db_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "KNOWLEDGE_DB_PATH", str(tmp_path / "none.db"))
    assert knowledge.recall("anything") == []


def test_stats(kb):
    assert knowledge.stats()["entries"] == 0
    knowledge.store("q1", "a1", [])
    knowledge.store("q2", "a2", [])
    assert knowledge.stats()["entries"] == 2


def test_recent_lists_newest_first(kb):
    first = knowledge.store("q1", "a1", ["scene.cpp"])
    second = knowledge.store("q2", "a2", [])
    rows = knowledge.recent(limit=10)
    assert [r["id"] for r in rows[:2]] == [second, first]
    assert rows[0]["question"] == "q2"
    assert rows[1]["refs"] == ["scene.cpp"]


# --- staleness (the make-or-break mechanism) -------------------------------


def test_recall_flags_stale_when_ref_changes(kb):
    knowledge.store("SceneMgr 作用", "旧结论", ["scene.cpp"])
    # mutate the referenced file -> hash changes -> entry must be flagged stale
    (kb / "scene.cpp").write_text("// SceneMgr impl v2 CHANGED\n", encoding="utf-8")
    hits = knowledge.recall("SceneMgr")
    assert hits[0]["stale"] is True
    assert "scene.cpp" in hits[0]["stale_refs"]


def test_recall_stale_when_ref_deleted(kb):
    knowledge.store("q about file", "ans", ["scene.cpp"])
    (kb / "scene.cpp").unlink()
    hits = knowledge.recall("file")
    assert hits[0]["stale"] is True


def test_no_refs_never_stale(kb):
    knowledge.store("general q", "general ans", [])
    assert knowledge.recall("general")[0]["stale"] is False


# --- synonym-expanded recall -----------------------------------------------


def test_recall_via_synonym(kb):
    # Stored with "作用"; queried with synonym "干嘛" must still recall.
    knowledge.store("SceneMgr 的作用", "场景管理", ["scene.cpp"])
    hits = knowledge.recall("SceneMgr 是干嘛的")
    assert hits and hits[0]["answer"] == "场景管理"


def test_recall_via_function_synonym(kb):
    knowledge.store("Update 这个函数做什么", "驱动场景更新", [])
    # "方法" is a synonym of "函数"; shared token SceneMgr/Update + synonym
    hits = knowledge.recall("Update 方法的功能")
    assert hits and "驱动" in hits[0]["answer"]


def test_fts_or_query_expands_synonyms():
    q = knowledge._fts_or_query("作用")
    assert '"功能"' in q and '"职责" ' in q + " "  # group members present


# --- agent integration -----------------------------------------------------


def test_agent_precipitates_after_answer(kb, monkeypatch):
    from code_agent.core import agent

    a = agent.CodeAgent()
    # stub the loop so no LLM is called; pretend it read scene.cpp
    import json
    from code_agent.core.events import Action

    def fake_loop():
        a.history = [Action("c1", "read_file", json.dumps({"path": "scene.cpp"}))]
        return "这是答案"

    monkeypatch.setattr(a, "_loop", fake_loop)
    out = a.run("解释 scene")
    assert out == "这是答案"
    # the Q&A must have been precipitated, with the read file as a ref
    hits = knowledge.recall("scene")
    assert hits and hits[0]["refs"] == ["scene.cpp"]


def test_agent_recalls_into_system_prompt(kb, monkeypatch):
    from code_agent.core import agent

    knowledge.store("旧问题 SceneMgr", "旧结论内容", ["scene.cpp"])
    a = agent.CodeAgent()
    a.recalled = a._recalled_context("SceneMgr 怎么用")
    assert "旧结论内容" in a.recalled
    # recalled context is injected into the system message. When prompt caching
    # is enabled the content is a list of typed blocks; either shape is fine.
    msgs = a._build_messages(with_tools=True)
    sys_content = msgs[0]["content"]
    sys_text = sys_content if isinstance(sys_content, str) else "".join(
        b.get("text", "") for b in sys_content
    )
    assert "旧结论内容" in sys_text


def test_flywheel_off_no_recall_no_store(kb, monkeypatch):
    from code_agent.core import agent

    monkeypatch.setattr(config, "USE_KNOWLEDGE", False)
    a = agent.CodeAgent()
    assert a._recalled_context("anything") == ""
    a.question = "q"
    a._precipitate("some answer")
    assert knowledge.stats()["entries"] == 0  # nothing stored when off
