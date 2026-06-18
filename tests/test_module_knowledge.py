"""Tests for versioned module knowledge cards."""
from code_agent import agent
from code_agent import config
from code_agent import module_knowledge


def test_recall_monster_config_card(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "CODE_REPOS", {})
    monkeypatch.setattr(config, "CODE_REPO_DEFAULT", "marvel")
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(tmp_path))
    cards = module_knowledge.recall("怪物如何配置，怪物技能在哪里配？")
    assert cards
    assert any("怪物配置" in c.title for c in cards)


def test_read_card_accepts_okf_style_tag_list(tmp_path):
    card_path = tmp_path / "card.md"
    card_path.write_text(
        "---\ntitle: 战斗框架\ntags: [combat, battle, 战斗]\n---\n\n# 战斗框架\n",
        encoding="utf-8",
    )
    card = module_knowledge._read_card(str(card_path))
    assert card is not None
    assert card.tags == ["combat", "battle", "战斗"]


def test_recall_cjk_compound_terms(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "CODE_REPOS", {})
    monkeypatch.setattr(config, "CODE_REPO_DEFAULT", "marvel")
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(tmp_path))
    cards = module_knowledge.recall("关卡刷怪流程")
    assert any("关卡框架" in c.title for c in cards)


def test_build_messages_injects_module_card(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "CODE_REPOS", {})
    monkeypatch.setattr(config, "CODE_REPO_DEFAULT", "marvel")
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(tmp_path))
    monkeypatch.setattr(config, "LLM_PROMPT_CACHE", False)
    a = agent.CodeAgent(mode="plain")
    a.question = "怪物如何配置？怪物技能配置缺失怎么排查？"
    msgs = a._build_messages(with_tools=True)
    assert "已命中的模块知识卡" in msgs[0]["content"]
    assert "SkillListForEnemy" in msgs[0]["content"]
