"""Tests for /ask /diagnose concurrency governance (thread-pool gate + timeout)."""
import concurrent.futures
import time

from code_agent.core import agent
from code_agent import config
from server import app as main
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_gate(monkeypatch):
    """Clean cache + reset the in-flight counter per test.

    Also drain the shared thread pool on exit so a slow test's still-running
    worker can't bleed its _inflight decrement into the next test.
    """
    main._CACHE.clear()
    monkeypatch.setattr(main, "_inflight", 0)
    yield
    # Let any in-flight pool worker finish before the next test inspects state.
    for _ in range(50):
        if main._inflight <= 0:
            break
        time.sleep(0.05)


def _client():
    return TestClient(main.app, raise_server_exceptions=False)


def test_normal_request_ok(monkeypatch):
    monkeypatch.setattr(agent, "answer", lambda q, *, verbose=False, mode=None, repo=None: f"A:{q}")
    r = _client().post("/ask", json={"question": "hi"})
    assert r.status_code == 200 and r.json()["answer"] == "A:hi"


def test_timeout_returns_504(monkeypatch):
    monkeypatch.setattr(config, "REQUEST_TIMEOUT", 0.2)

    def slow(q, *, verbose=False, mode=None, repo=None):
        time.sleep(1.0)
        return "too late"

    monkeypatch.setattr(agent, "answer", slow)
    r = _client().post("/ask", json={"question": "slow"})
    assert r.status_code == 504
    assert "超时" in r.json()["detail"]


def test_queue_overflow_returns_503(monkeypatch):
    # cap = MAX_CONCURRENCY + MAX_QUEUE. Saturate it, then the next call 503s.
    monkeypatch.setattr(config, "MAX_CONCURRENCY", 1)
    monkeypatch.setattr(config, "MAX_QUEUE", 0)
    # Pretend the single slot is already occupied by an in-flight request.
    monkeypatch.setattr(main, "_inflight", 1)

    import asyncio

    async def scenario():
        with pytest.raises(main.HTTPException) as ei:
            await main._run_governed(lambda: "x")
        assert ei.value.status_code == 503

    asyncio.run(scenario())


def test_inflight_released_after_completion(monkeypatch):
    """A normal request increments then decrements _inflight (no leak)."""
    monkeypatch.setattr(agent, "answer", lambda q, *, verbose=False, mode=None, repo=None: "ok")
    c = _client()
    c.post("/ask", json={"question": "q1"})
    # give the done-callback a moment to marshal back to the loop
    time.sleep(0.1)
    assert main._inflight == 0


def test_timeout_does_not_free_slot_until_thread_done(monkeypatch):
    """On 504 the slot stays held until the real thread finishes (cap honored)."""
    monkeypatch.setattr(config, "REQUEST_TIMEOUT", 0.15)
    release = []

    def slow(q, *, verbose=False, mode=None, repo=None):
        time.sleep(0.5)
        release.append(1)
        return "late"

    monkeypatch.setattr(agent, "answer", slow)
    r = _client().post("/ask", json={"question": "q"})
    assert r.status_code == 504
    # Right after the 504, the worker thread is still running → slot NOT freed.
    assert main._inflight == 1
    # After the thread actually finishes, the slot frees.
    time.sleep(0.6)
    assert release and main._inflight == 0


def test_cache_hit_skips_gate(monkeypatch):
    """A cached answer returns without consuming a slot."""
    calls = {"n": 0}

    def once(q, *, verbose=False, mode=None, repo=None):
        calls["n"] += 1
        return "cached-me"

    monkeypatch.setattr(agent, "answer", once)
    c = _client()
    c.post("/ask", json={"question": "q"})           # populates cache
    r = c.post("/ask", json={"question": "q"})         # served from cache
    assert r.json()["cached"] is True
    assert calls["n"] == 1
