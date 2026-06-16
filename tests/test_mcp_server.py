"""Tests for the MCP server adapter (offline — agent.answer is monkeypatched).

The tool is registered on FastMCP; we exercise it both directly (the wrapped
function) and through the MCP server's tool registry to prove it's discoverable.
"""
import agent
import mcp_server
import pytest


def test_ask_codebase_delegates_to_agent(monkeypatch):
    monkeypatch.setattr(agent, "answer", lambda q, *, verbose=False: f"A: {q}")
    assert mcp_server.ask_codebase("什么是 SceneMgr？") == "A: 什么是 SceneMgr？"


def test_ask_codebase_empty_question(monkeypatch):
    called = {"n": 0}

    def spy(q, *, verbose=False):
        called["n"] += 1
        return "x"

    monkeypatch.setattr(agent, "answer", spy)
    assert mcp_server.ask_codebase("   ") == "问题不能为空。"
    assert called["n"] == 0  # never reaches the agent


def test_diagnose_crash_accepts_log_without_backtrace(monkeypatch):
    import diagnose

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
    import diagnose

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
