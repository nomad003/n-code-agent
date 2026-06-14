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


@pytest.mark.anyio
async def test_tool_is_registered():
    tools = await mcp_server.mcp.list_tools()
    names = [t.name for t in tools]
    assert "ask_codebase" in names


@pytest.fixture
def anyio_backend():
    return "asyncio"
