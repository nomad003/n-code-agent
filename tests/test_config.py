"""Tests for config helpers and the agent backend dispatch."""
from code_agent import config
from code_agent.core import operation_modes
import pytest


def test_require_api_key_raises_when_empty(monkeypatch):
    monkeypatch.setattr(config, "LLM_API_KEY", "")
    with pytest.raises(RuntimeError):
        config.require_api_key()


def test_require_api_key_returns_value(monkeypatch):
    monkeypatch.setattr(config, "LLM_API_KEY", "sk-test")
    assert config.require_api_key() == "sk-test"


def test_system_prompt_enforces_concise_structured_no_code_by_default():
    prompt = config.SYSTEM_PROMPT
    assert "简单、精确、结构化" in prompt
    assert "严禁输出任何代码片段" in prompt
    assert "即使用户要求代码或示例" in prompt
    assert "只用结构化文字描述" in prompt
    assert "不展开底层实现" in prompt


def test_system_prompt_for_technical_mode(monkeypatch):
    monkeypatch.setattr(config, "AGENT_ALLOWED_MODES", ("plain", "technical"))
    prompt = config.system_prompt_for_mode("technical")
    assert "第 2 档" in prompt
    assert "面向程序员" in prompt
    assert "不直接修改代码" in prompt


def test_disabled_mode_is_rejected(monkeypatch):
    monkeypatch.setattr(config, "AGENT_ALLOWED_MODES", ("plain",))
    with pytest.raises(operation_modes.ModeError):
        config.system_prompt_for_mode("technical")


def test_routed_model_adds_openai_prefix(monkeypatch):
    from code_agent.core import agent

    monkeypatch.setattr(config, "LLM_MODEL", "vertex_ai/gemini-3.5-flash")
    assert agent._routed_model() == "openai/vertex_ai/gemini-3.5-flash"


def test_routed_model_idempotent(monkeypatch):
    from code_agent.core import agent

    monkeypatch.setattr(config, "LLM_MODEL", "openai/already")
    assert agent._routed_model() == "openai/already"


def test_answer_dispatches_to_custom(monkeypatch):
    from code_agent.core import agent

    monkeypatch.setattr(config, "AGENT_BACKEND", "custom")
    monkeypatch.setattr(config, "AGENT_ALLOWED_MODES", ("plain",))
    monkeypatch.setattr(agent.CodeAgent, "run", lambda self, q: f"custom:{q}")
    assert agent.answer("hi") == "custom:hi"


def test_answer_enforces_response_policy(monkeypatch):
    from code_agent.core import agent

    monkeypatch.setattr(config, "AGENT_BACKEND", "custom")
    monkeypatch.setattr(config, "AGENT_ALLOWED_MODES", ("plain",))
    monkeypatch.setattr(agent.CodeAgent, "run", lambda self, q: "说明\n```python\nprint(1)\n```")
    out = agent.answer("hi")
    assert "print" not in out
    assert "输出策略" in out


def test_answer_dispatches_to_sdk(monkeypatch):
    """sdk path must not import litellm-side code; we stub the lazy import."""
    import sys
    import types

    from code_agent.core import agent

    fake = types.ModuleType("code_agent.core.agent_sdk")
    captured = {}

    def fake_answer(q, *, verbose=False, mode="plain", trace=None):
        captured["mode"] = mode
        captured["trace"] = trace
        return f"sdk:{q}"

    fake.answer = fake_answer
    monkeypatch.setitem(sys.modules, "code_agent.core.agent_sdk", fake)
    monkeypatch.setattr(config, "AGENT_BACKEND", "sdk")
    monkeypatch.setattr(config, "AGENT_ALLOWED_MODES", ("plain", "technical"))
    assert agent.answer("hi", mode="technical") == "sdk:hi"
    assert captured["mode"] == "technical"
    assert captured["trace"] is not None


def test_repo_context_selects_repo_paths(monkeypatch, tmp_path):
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

    assert config.current_repo().name == "gameserver"
    assert config.current_target_code_path() == str(g)
    with config.use_repo("ecs"):
        assert config.current_repo().name == "ecs"
        assert config.current_target_code_path() == str(e)
        assert config.current_index_db_path() == str(tmp_path / "e.db")
    assert config.current_repo().name == "gameserver"


def test_unknown_repo_is_rejected(monkeypatch, tmp_path):
    root = tmp_path / "gameserver"
    root.mkdir()
    monkeypatch.setattr(
        config,
        "CODE_REPOS",
        {
            "gameserver": config.CodeRepo("gameserver", str(root), str(tmp_path / "g.db"), str(tmp_path / "gk.db"), str(tmp_path / "gp.json")),
        },
    )
    monkeypatch.setattr(config, "CODE_REPO_DEFAULT", "gameserver")

    with pytest.raises(ValueError):
        config.resolve_repo_name("ecs")
