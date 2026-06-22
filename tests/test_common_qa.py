"""Tests for maintained common Q&A cards."""
import types

from code_agent import config
from code_agent.core import agent
from code_agent.kb import common_qa


def _write_common_qa(tmp_path, name, content):
    root = tmp_path / "docs" / "code-knowledge" / "marvel" / "common-qa"
    root.mkdir(parents=True, exist_ok=True)
    path = root / name
    path.write_text(content, encoding="utf-8")


def test_common_qa_matches_declared_question(monkeypatch, tmp_path):
    _write_common_qa(
        tmp_path,
        "monster-config.md",
        (
            "---\n"
            "type: Common QA\n"
            "title: 怪物配置\n"
            "questions: 怪物配置, 怪物怎么配置\n"
            "aliases: monster config\n"
            "tags: qa, enemy, config\n"
            "---\n\n"
            "# 怪物配置\n\n编辑好的答案。\n"
        ),
    )
    monkeypatch.setattr(config, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(config, "CODE_REPOS", {})
    monkeypatch.setattr(config, "CODE_REPO_DEFAULT", "marvel")
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(tmp_path))

    hit = common_qa.find_match("怪物怎么配置？")
    assert hit is not None
    assert hit.title == "怪物配置"
    assert "编辑好的答案" in common_qa.answer_if_match("怪物配置")
    assert common_qa.answer_if_match("怪物") is None


def test_agent_returns_common_qa_without_llm_loop(monkeypatch, tmp_path):
    _write_common_qa(
        tmp_path,
        "monster-config.md",
        (
            "---\n"
            "type: Common QA\n"
            "title: 怪物配置\n"
            "questions: 怪物配置, 怪物怎么配置\n"
            "---\n\n"
            "# 怪物配置\n\n这是维护好的答案。\n"
        ),
    )
    monkeypatch.setattr(config, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(config, "CODE_REPOS", {})
    monkeypatch.setattr(config, "CODE_REPO_DEFAULT", "marvel")
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(tmp_path))
    monkeypatch.setattr(config, "USE_SHORTCUT", False)
    monkeypatch.setattr(config, "AGENT_BACKEND", "custom")
    monkeypatch.setattr(config, "AGENT_ALLOWED_MODES", ("plain", "technical"))
    monkeypatch.setattr(
        agent.CodeAgent,
        "run",
        lambda self, q: (_ for _ in ()).throw(AssertionError("should not run LLM loop")),
    )

    assert "维护好的答案" in agent.answer("怪物怎么配置？", mode="technical")


def test_agent_uses_llm_router_for_common_qa_intent(monkeypatch, tmp_path):
    _write_common_qa(
        tmp_path,
        "monster-config.md",
        (
            "---\n"
            "type: Common QA\n"
            "title: 怪物配置\n"
            "questions: 怪物配置, 怪物怎么配置\n"
            "---\n\n"
            "# 怪物配置\n\n这是 LLM 路由命中的答案。\n"
        ),
    )
    monkeypatch.setattr(config, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(config, "CODE_REPOS", {})
    monkeypatch.setattr(config, "CODE_REPO_DEFAULT", "marvel")
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(tmp_path))
    monkeypatch.setattr(config, "USE_SHORTCUT", False)
    monkeypatch.setattr(config, "AGENT_BACKEND", "custom")
    monkeypatch.setattr(config, "AGENT_ALLOWED_MODES", ("plain", "technical"))
    monkeypatch.setattr(config, "LLM_API_KEY", "sk-test")
    assert common_qa.find_match("怪物的配置") is None
    assert [item.path for item in common_qa.llm_candidates("怪物的配置")] == [
        "common-qa/monster-config.md"
    ]

    calls = []

    def fake_completion(**kwargs):
        calls.append(kwargs)
        msg = types.SimpleNamespace(content='{"path":"common-qa/monster-config.md"}')
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])

    monkeypatch.setattr(agent.litellm, "completion", fake_completion)
    monkeypatch.setattr(
        agent.CodeAgent,
        "run",
        lambda self, q: (_ for _ in ()).throw(AssertionError("should not run LLM loop")),
    )

    out = agent.answer("怪物的配置", mode="technical")
    assert "LLM 路由命中的答案" in out
    assert calls
    assert "通用问答集意图路由器" in calls[0]["messages"][0]["content"]


def test_specific_code_identifier_bypasses_common_qa(monkeypatch, tmp_path):
    _write_common_qa(
        tmp_path,
        "buff-config.md",
        (
            "---\n"
            "type: Common QA\n"
            "title: Buff 配置\n"
            "questions: Buff配置, Buff怎么配置\n"
            "aliases: InBornBuff 配置, BuffTable 配置\n"
            "---\n\n"
            "# Buff 配置\n\n总览答案。\n"
        ),
    )
    monkeypatch.setattr(config, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(config, "CODE_REPOS", {})
    monkeypatch.setattr(config, "CODE_REPO_DEFAULT", "marvel")
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(tmp_path))

    assert common_qa.find_match("Buff怎么配置", repo="marvel").title == "Buff 配置"
    assert common_qa.find_match("InBornBuff怎么配置", repo="marvel") is None
    assert common_qa.llm_candidates("InBornBuff怎么配置", repo="marvel") == []
    assert common_qa.specific_code_identifiers("InBornBuff怎么配置") == ["InBornBuff"]


def test_agent_specific_code_identifier_enters_agent_loop(monkeypatch, tmp_path):
    _write_common_qa(
        tmp_path,
        "buff-config.md",
        (
            "---\n"
            "type: Common QA\n"
            "title: Buff 配置\n"
            "questions: Buff配置, Buff怎么配置\n"
            "aliases: InBornBuff 配置\n"
            "---\n\n"
            "# Buff 配置\n\n总览答案。\n"
        ),
    )
    monkeypatch.setattr(config, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(config, "CODE_REPOS", {})
    monkeypatch.setattr(config, "CODE_REPO_DEFAULT", "marvel")
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(tmp_path))
    monkeypatch.setattr(config, "USE_SHORTCUT", False)
    monkeypatch.setattr(config, "AGENT_BACKEND", "custom")
    monkeypatch.setattr(config, "AGENT_ALLOWED_MODES", ("plain", "technical"))
    monkeypatch.setattr(agent.CodeAgent, "run", lambda self, q: f"loop:{q}")

    assert agent.answer("InBornBuff怎么配置", mode="technical") == "loop:InBornBuff怎么配置"


def test_common_qa_llm_router_none_falls_through(monkeypatch, tmp_path):
    _write_common_qa(
        tmp_path,
        "monster-config.md",
        (
            "---\n"
            "type: Common QA\n"
            "title: 怪物配置\n"
            "questions: 怪物配置\n"
            "---\n\n"
            "# 怪物配置\n\n维护答案。\n"
        ),
    )
    monkeypatch.setattr(config, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(config, "CODE_REPOS", {})
    monkeypatch.setattr(config, "CODE_REPO_DEFAULT", "marvel")
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(tmp_path))
    monkeypatch.setattr(config, "USE_SHORTCUT", False)
    monkeypatch.setattr(config, "AGENT_BACKEND", "custom")
    monkeypatch.setattr(config, "AGENT_ALLOWED_MODES", ("plain", "technical"))
    monkeypatch.setattr(config, "LLM_API_KEY", "sk-test")

    def fake_completion(**_kwargs):
        msg = types.SimpleNamespace(content='{"path":"none"}')
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])

    monkeypatch.setattr(agent.litellm, "completion", fake_completion)
    monkeypatch.setattr(agent.CodeAgent, "run", lambda self, q: f"loop:{q}")

    assert agent.answer("怪物性能怎么配置", mode="technical") == "loop:怪物性能怎么配置"


def test_builtin_big_module_common_qa_cards_are_matchable():
    items = common_qa.load("marvel", include_common=False)
    titles = {item.title for item in items}
    assert {
        "AI 配置",
        "Buff 配置",
        "Skill 配置",
        "SkillSlot 配置",
        "关卡 Level 配置",
        "场景配置",
    } <= titles

    expected = {
        "Buff的配置": "Buff 配置",
        "Skill的配置": "Skill 配置",
        "SkillSlot怎么配置": "SkillSlot 配置",
        "关卡Level的配置": "关卡 Level 配置",
        "场景的配置": "场景配置",
        "AI的配置": "AI 配置",
    }
    for question, title in expected.items():
        hit = common_qa.find_match(question, repo="marvel")
        assert hit is not None
        assert hit.title == title
