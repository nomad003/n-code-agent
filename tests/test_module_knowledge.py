"""Tests for versioned module knowledge cards."""
from code_agent import agent
from code_agent import config
from code_agent import module_knowledge


def _write_knowledge_card(tmp_path, name, content):
    root = tmp_path / "docs" / "code-knowledge" / "marvel"
    root.mkdir(parents=True, exist_ok=True)
    (root / name).write_text(content, encoding="utf-8")


def test_recall_monster_config_card(monkeypatch, tmp_path):
    _write_knowledge_card(
        tmp_path,
        "monster-config.md",
        (
            "---\n"
            "title: 怪物配置与敌人技能配置链路\n"
            "tags: 怪物, monster, enemy, 技能, 配置\n"
            "symbols: CombatEnemy, SkillListForEnemy\n"
            "---\n\n"
            "# 怪物配置\n\n怪物技能通过 SkillListForEnemy 配置。\n"
        ),
    )
    monkeypatch.setattr(config, "PROJECT_ROOT", str(tmp_path))
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
    _write_knowledge_card(
        tmp_path,
        "level-framework.md",
        (
            "---\n"
            "title: 关卡框架\n"
            "tags: 关卡, 刷怪, level, spawner\n"
            "---\n\n"
            "# 关卡框架\n\n关卡刷怪流程由 LevelSpawner 处理。\n"
        ),
    )
    monkeypatch.setattr(config, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(config, "CODE_REPOS", {})
    monkeypatch.setattr(config, "CODE_REPO_DEFAULT", "marvel")
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(tmp_path))
    cards = module_knowledge.recall("关卡刷怪流程")
    assert any("关卡框架" in c.title for c in cards)


def test_load_cards_recurses_okf_bundle(monkeypatch, tmp_path):
    root = tmp_path / "docs" / "code-knowledge" / "marvel" / "gameserver"
    root.mkdir(parents=True)
    (root / "nested.md").write_text(
        "---\ntitle: 嵌套模块\ntags: nested, scene\n---\n\n# 嵌套模块\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(config, "CODE_REPOS", {})
    monkeypatch.setattr(config, "CODE_REPO_DEFAULT", "marvel")
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(tmp_path / "target"))

    cards = module_knowledge.load_cards()
    assert any(c.path.endswith("gameserver/nested.md") for c in cards)
    assert any(c.title == "嵌套模块" for c in module_knowledge.recall("nested scene"))


def test_build_messages_injects_module_card(monkeypatch, tmp_path):
    _write_knowledge_card(
        tmp_path,
        "monster-config.md",
        (
            "---\n"
            "type: Config Chain\n"
            "title: 怪物配置与敌人技能配置链路\n"
            "description: 怪物配置和 enemy skill not find 排查。\n"
            "tags: 怪物, monster, enemy, 技能, 配置\n"
            "symbols: SkillListForEnemy, GetEnemySkillConfigX\n"
            "logs: enemy conf skill, skill not find in conf\n"
            "---\n\n"
            "# 怪物配置\n\nSkillListForEnemy 是怪物技能配置排查入口。\n"
        ),
    )
    monkeypatch.setattr(config, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(config, "CODE_REPOS", {})
    monkeypatch.setattr(config, "CODE_REPO_DEFAULT", "marvel")
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(tmp_path))
    monkeypatch.setattr(config, "LLM_PROMPT_CACHE", False)
    a = agent.CodeAgent(mode="plain")
    a.question = "怪物如何配置？怪物技能配置缺失怎么排查？"
    msgs = a._build_messages(with_tools=True)
    assert "代码知识库地图" in msgs[0]["content"]
    assert "已命中的模块知识卡" in msgs[0]["content"]
    assert "SkillListForEnemy" in msgs[0]["content"]
