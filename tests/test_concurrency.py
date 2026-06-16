"""Tests for /ask /diagnose concurrency governance (semaphore + queue + timeout)."""
import asyncio
import time

import agent
import config
import main
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_gate(monkeypatch):
    """Fresh semaphore/queue per test and a clean cache."""
    main._CACHE.clear()
    monkeypatch.setattr(main, "_waiting", 0)
    yield


def _client():
    return TestClient(main.app, raise_server_exceptions=False)


def test_normal_request_ok(monkeypatch):
    monkeypatch.setattr(agent, "answer", lambda q, *, verbose=False: f"A:{q}")
    r = _client().post("/ask", json={"question": "hi"})
    assert r.status_code == 200 and r.json()["answer"] == "A:hi"


def test_timeout_returns_504(monkeypatch):
    monkeypatch.setattr(config, "REQUEST_TIMEOUT", 0.2)
    monkeypatch.setattr(main, "_sema", asyncio.Semaphore(config.MAX_CONCURRENCY))

    def slow(q, *, verbose=False):
        time.sleep(1.0)
        return "too late"

    monkeypatch.setattr(agent, "answer", slow)
    r = _client().post("/ask", json={"question": "slow"})
    assert r.status_code == 504
    assert "超时" in r.json()["detail"]


def test_queue_overflow_returns_503(monkeypatch):
    # 1 slot, 0 queue: the 2nd concurrent request must be shed with 503.
    monkeypatch.setattr(config, "MAX_CONCURRENCY", 1)
    monkeypatch.setattr(config, "MAX_QUEUE", 0)
    monkeypatch.setattr(main, "_sema", asyncio.Semaphore(1))

    started = asyncio.Event()

    async def scenario():
        async def occupy():
            # Hold the only slot by simulating an in-flight governed call.
            await main._sema.acquire()
            started.set()
            try:
                await asyncio.sleep(0.3)
            finally:
                main._sema.release()

        holder = asyncio.create_task(occupy())
        await started.wait()
        # Now the slot is taken and queue=0 → governed run must 503.
        with pytest.raises(main.HTTPException) as ei:
            await main._run_governed(lambda: "x")
        assert ei.value.status_code == 503
        await holder

    asyncio.run(scenario())


def test_cache_hit_skips_gate(monkeypatch):
    """A cached answer returns without touching the concurrency gate."""
    calls = {"n": 0}

    def once(q, *, verbose=False):
        calls["n"] += 1
        return "cached-me"

    monkeypatch.setattr(agent, "answer", once)
    c = _client()
    c.post("/ask", json={"question": "q"})           # populates cache
    r = c.post("/ask", json={"question": "q"})         # served from cache
    assert r.json()["cached"] is True
    assert calls["n"] == 1
