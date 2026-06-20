"""Tests for the MCP server adapter (offline — agent.answer is monkeypatched).

The tool is registered on FastMCP; we exercise it both directly (the wrapped
function) and through the MCP server's tool registry to prove it's discoverable.
"""
from code_agent.core import agent
from code_agent import config
from code_agent.interfaces import mcp_server
import pytest


def test_ask_codebase_delegates_to_agent(monkeypatch):
    monkeypatch.setattr(config, "AGENT_ALLOWED_MODES", ("plain",))
    monkeypatch.setattr(agent, "answer", lambda q, *, verbose=False, mode=None, repo=None: f"A: {q}")
    assert mcp_server.ask_codebase("什么是 SceneMgr？") == "A: 什么是 SceneMgr？"


def test_ask_codebase_empty_question(monkeypatch):
    called = {"n": 0}

    def spy(q, *, verbose=False, mode=None, repo=None):
        called["n"] += 1
        return "x"

    monkeypatch.setattr(agent, "answer", spy)
    assert mcp_server.ask_codebase("   ") == "问题不能为空。"
    assert called["n"] == 0  # never reaches the agent


def test_ask_codebase_rejects_disabled_mode(monkeypatch):
    called = {"n": 0}

    def spy(q, *, verbose=False, mode=None, repo=None):
        called["n"] += 1
        return "x"

    monkeypatch.setattr(config, "AGENT_ALLOWED_MODES", ("plain",))
    monkeypatch.setattr(agent, "answer", spy)
    out = mcp_server.ask_codebase("Q", mode="technical")
    assert "模式不可用" in out
    assert called["n"] == 0


def test_ask_codebase_passes_enabled_mode(monkeypatch):
    captured = {}

    def fake_answer(q, *, verbose=False, mode=None, repo=None):
        captured["mode"] = mode
        captured["repo"] = repo
        return "ok"

    monkeypatch.setattr(config, "AGENT_ALLOWED_MODES", ("plain", "technical"))
    monkeypatch.setattr(agent, "answer", fake_answer)
    assert mcp_server.ask_codebase("Q", mode="technical") == "ok"
    assert captured["mode"] == "technical"
    assert captured["repo"] == "default"


def test_diagnose_crash_accepts_log_without_backtrace(monkeypatch):
    from code_agent.diagnostics import diagnose

    captured = {}

    def fake_diagnose(backtrace, *, extra_log="", verbose=False, with_plain=False):
        captured["backtrace"] = backtrace
        captured["extra_log"] = extra_log
        return {
            "answer": "日志诊断结论",
            "frames": [],
            "resolved": 0,
            "total_frames": 0,
        }

    monkeypatch.setattr(diagnose, "diagnose", fake_diagnose)
    assert mcp_server.diagnose_crash("", "ERROR player not found") == "日志诊断结论"
    assert captured == {"backtrace": "", "extra_log": "ERROR player not found"}


def test_diagnose_crash_rejects_empty_input(monkeypatch):
    from code_agent.diagnostics import diagnose

    called = {"n": 0}

    def fake_diagnose(*args, **kwargs):
        called["n"] += 1
        return {"answer": "x", "frames": [], "resolved": 0, "total_frames": 0}

    monkeypatch.setattr(diagnose, "diagnose", fake_diagnose)
    assert mcp_server.diagnose_crash(" ", " ") == "backtrace 和 log_snippet 不能同时为空。"
    assert called["n"] == 0


@pytest.mark.anyio
async def test_tool_is_registered():
    tools = await mcp_server.mcp.list_tools()
    names = [t.name for t in tools]
    assert "ask_codebase" in names
    assert "diagnose_crash" in names
    assert set(names) == {"ask_codebase", "diagnose_crash"}


@pytest.fixture
def anyio_backend():
    return "asyncio"
