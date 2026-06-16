"""Tests for the FastAPI service and its caching layer.

agent.answer is stubbed so no LLM is called; we count invocations to prove the
cache short-circuits repeated questions.
"""
import agent
import main
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    main._CACHE.clear()
    calls = {"n": 0}

    def fake_answer(question, *, verbose=False):
        calls["n"] += 1
        return f"answer-{calls['n']}: {question}"

    monkeypatch.setattr(agent, "answer", fake_answer)
    c = TestClient(main.app)
    c.calls = calls  # expose the counter to tests
    return c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


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

    def boom(question, *, verbose=False):
        raise RuntimeError("ExceededBudget")

    monkeypatch.setattr(agent, "answer", boom)
    c = TestClient(main.app, raise_server_exceptions=False)
    r = c.post("/ask", json={"question": "Q"})
    assert r.status_code == 502
    assert "ExceededBudget" in r.json()["detail"]


def test_failure_is_not_cached(monkeypatch):
    main._CACHE.clear()
    state = {"fail": True}

    def flaky(question, *, verbose=False):
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
    import config

    main._CACHE.clear()
    monkeypatch.setattr(config, "CACHE_MAX_ENTRIES", 3)
    monkeypatch.setattr(agent, "answer", lambda q, *, verbose=False: f"a:{q}")
    c = TestClient(main.app)
    for i in range(5):
        c.post("/ask", json={"question": f"q{i}"})
    # never exceeds the cap
    assert len(main._CACHE) == 3
    # oldest (q0, q1) evicted; newest kept
    assert "q0" not in main._CACHE and "q4" in main._CACHE


def test_cache_disabled_when_max_zero(monkeypatch):
    import config

    main._CACHE.clear()
    monkeypatch.setattr(config, "CACHE_MAX_ENTRIES", 0)
    monkeypatch.setattr(agent, "answer", lambda q, *, verbose=False: "x")
    c = TestClient(main.app)
    c.post("/ask", json={"question": "q"})
    assert len(main._CACHE) == 0  # nothing cached
