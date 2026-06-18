"""Tests for the FastAPI service and its caching layer.

agent.answer is stubbed so no LLM is called; we count invocations to prove the
cache short-circuits repeated questions.
"""
from code_agent import agent
from code_agent import config
from code_agent import main
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    main._CACHE.clear()
    calls = {"n": 0}

    monkeypatch.setattr(config, "AGENT_ALLOWED_MODES", ("plain",))

    def fake_answer(question, **kwargs):
        calls["n"] += 1
        repo = kwargs.get("repo")
        return f"answer-{calls['n']}: {repo}:{question}"

    monkeypatch.setattr(agent, "answer", fake_answer)
    c = TestClient(main.app)
    c.calls = calls  # expose the counter to tests
    return c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_ui_page(client):
    r = client.get("/ui")
    assert r.status_code == 200
    assert "Code Agent 提问测试" in r.text
    assert "question_type" in r.text


def test_ask_returns_answer(client):
    r = client.post("/ask", json={"question": "什么是 SceneMgr？"})
    assert r.status_code == 200
    body = r.json()
    assert body["cached"] is False
    assert "什么是 SceneMgr？" in body["answer"]
    assert client.calls["n"] == 1


def test_ask_empty_question(client):
    r = client.post("/ask", json={"question": "   "})
    assert r.json() == {"answer": "问题不能为空。", "cached": False}
    assert client.calls["n"] == 0  # never reaches the agent


def test_cache_hit_skips_agent(client):
    first = client.post("/ask", json={"question": "Q"}).json()
    second = client.post("/ask", json={"question": "Q"}).json()
    assert first["cached"] is False
    assert second["cached"] is True
    assert first["answer"] == second["answer"]  # same cached value
    assert client.calls["n"] == 1  # agent called only once


def test_use_cache_false_always_calls_agent(client):
    client.post("/ask", json={"question": "Q", "use_cache": False})
    r = client.post("/ask", json={"question": "Q", "use_cache": False})
    assert r.json()["cached"] is False
    assert client.calls["n"] == 2  # no caching either way


def test_agent_failure_returns_502(monkeypatch):
    main._CACHE.clear()

    def boom(question, **kwargs):
        raise RuntimeError("ExceededBudget")

    monkeypatch.setattr(agent, "answer", boom)
    c = TestClient(main.app, raise_server_exceptions=False)
    r = c.post("/ask", json={"question": "Q"})
    assert r.status_code == 502
    assert "ExceededBudget" in r.json()["detail"]


def test_failure_is_not_cached(monkeypatch):
    main._CACHE.clear()
    state = {"fail": True}

    def flaky(question, **kwargs):
        if state["fail"]:
            raise RuntimeError("transient")
        return "ok now"

    monkeypatch.setattr(agent, "answer", flaky)
    c = TestClient(main.app, raise_server_exceptions=False)
    assert c.post("/ask", json={"question": "Q"}).status_code == 502
    # Recover: the failed question must not have been cached.
    state["fail"] = False
    r = c.post("/ask", json={"question": "Q"})
    assert r.status_code == 200
    assert r.json() == {"answer": "ok now", "cached": False}


def test_cache_is_lru_bounded(monkeypatch):
    main._CACHE.clear()
    monkeypatch.setattr(config, "CACHE_MAX_ENTRIES", 3)
    monkeypatch.setattr(agent, "answer", lambda q, **kwargs: f"a:{q}")
    c = TestClient(main.app)
    for i in range(5):
        c.post("/ask", json={"question": f"q{i}"})
    # never exceeds the cap
    assert len(main._CACHE) == 3
    # oldest (q0, q1) evicted; newest kept
    assert ("default", "plain", "", "q0") not in main._CACHE
    assert ("default", "plain", "", "q4") in main._CACHE


def test_cache_disabled_when_max_zero(monkeypatch):
    main._CACHE.clear()
    monkeypatch.setattr(config, "CACHE_MAX_ENTRIES", 0)
    monkeypatch.setattr(agent, "answer", lambda q, **kwargs: "x")
    c = TestClient(main.app)
    c.post("/ask", json={"question": "q"})
    assert len(main._CACHE) == 0  # nothing cached


def test_ask_rejects_disabled_mode(client):
    r = client.post("/ask", json={"question": "Q", "mode": "technical"})
    assert r.status_code == 403
    assert "disabled" in r.json()["detail"]
    assert client.calls["n"] == 0


def test_ask_uses_enabled_mode_and_separate_cache(monkeypatch):
    main._CACHE.clear()
    monkeypatch.setattr(config, "AGENT_ALLOWED_MODES", ("plain", "technical"))
    calls = []

    def fake_answer(question, **kwargs):
        mode = kwargs.get("mode")
        calls.append(mode)
        return f"{mode}:{question}"

    monkeypatch.setattr(agent, "answer", fake_answer)
    c = TestClient(main.app)
    assert c.post("/ask", json={"question": "Q"}).json()["answer"] == "plain:Q"
    assert c.post("/ask", json={"question": "Q", "mode": "technical"}).json()["answer"] == "technical:Q"
    assert c.post("/ask", json={"question": "Q", "mode": "technical"}).json()["cached"] is True
    assert calls == ["plain", "technical"]


def test_ask_uses_question_type_and_separate_cache(monkeypatch):
    main._CACHE.clear()
    seen = []

    def fake_answer(question, **kwargs):
        seen.append(kwargs.get("question_type"))
        return f"{kwargs.get('question_type')}:{question}"

    monkeypatch.setattr(agent, "answer", fake_answer)
    c = TestClient(main.app)
    assert c.post("/ask", json={"question": "Q", "question_type": "outage_log"}).json()["answer"] == "outage_log:Q"
    assert c.post("/ask", json={"question": "Q", "question_type": "feature_impl"}).json()["answer"] == "feature_impl:Q"
    assert c.post("/ask", json={"question": "Q", "question_type": "feature_impl"}).json()["cached"] is True
    assert seen == ["outage_log", "feature_impl"]


def test_ask_rejects_unknown_question_type(client):
    r = client.post("/ask", json={"question": "Q", "question_type": "wrong"})
    assert r.status_code == 400
    assert "unknown question_type" in r.json()["detail"]


def test_ask_uses_repo_and_separate_cache(monkeypatch, tmp_path):
    main._CACHE.clear()
    g = tmp_path / "gameserver"
    e = tmp_path / "ecs"
    g.mkdir()
    e.mkdir()
    monkeypatch.setattr(
        config,
        "CODE_REPOS",
        {
            "gameserver": config.CodeRepo("gameserver", str(g), str(tmp_path / "g.db"), str(tmp_path / "gk.db"), str(tmp_path / "gp.json")),
            "ecs": config.CodeRepo("ecs", str(e), str(tmp_path / "e.db"), str(tmp_path / "ek.db"), str(tmp_path / "ep.json")),
        },
    )
    monkeypatch.setattr(config, "CODE_REPO_DEFAULT", "gameserver")
    calls = []

    def fake_answer(question, **kwargs):
        repo = kwargs.get("repo")
        calls.append(repo)
        return f"{repo}:{question}"

    monkeypatch.setattr(agent, "answer", fake_answer)
    c = TestClient(main.app)
    assert c.post("/ask", json={"question": "Q"}).json()["answer"] == "gameserver:Q"
    assert c.post("/ask", json={"question": "Q", "repo": "ecs"}).json()["answer"] == "ecs:Q"
    assert c.post("/ask", json={"question": "Q", "repo": "ecs"}).json()["cached"] is True
    assert calls == ["gameserver", "ecs"]
