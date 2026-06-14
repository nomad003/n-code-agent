"""Tests for config helpers and the agent backend dispatch."""
import config
import pytest


def test_require_api_key_raises_when_empty(monkeypatch):
    monkeypatch.setattr(config, "LLM_API_KEY", "")
    with pytest.raises(RuntimeError):
        config.require_api_key()


def test_require_api_key_returns_value(monkeypatch):
    monkeypatch.setattr(config, "LLM_API_KEY", "sk-test")
    assert config.require_api_key() == "sk-test"


def test_routed_model_adds_openai_prefix(monkeypatch):
    import agent

    monkeypatch.setattr(config, "LLM_MODEL", "vertex_ai/gemini-3.5-flash")
    assert agent._routed_model() == "openai/vertex_ai/gemini-3.5-flash"


def test_routed_model_idempotent(monkeypatch):
    import agent

    monkeypatch.setattr(config, "LLM_MODEL", "openai/already")
    assert agent._routed_model() == "openai/already"


def test_answer_dispatches_to_custom(monkeypatch):
    import agent

    monkeypatch.setattr(config, "AGENT_BACKEND", "custom")
    monkeypatch.setattr(agent, "_answer_custom", lambda q, *, verbose=False: f"custom:{q}")
    assert agent.answer("hi") == "custom:hi"


def test_answer_dispatches_to_sdk(monkeypatch):
    """sdk path must not import litellm-side code; we stub the lazy import."""
    import sys
    import types

    import agent

    fake = types.ModuleType("agent_sdk")
    fake.answer = lambda q, *, verbose=False: f"sdk:{q}"
    monkeypatch.setitem(sys.modules, "agent_sdk", fake)
    monkeypatch.setattr(config, "AGENT_BACKEND", "sdk")
    assert agent.answer("hi") == "sdk:hi"
