"""Tests for versioned module knowledge cards."""
from code_agent.core import agent
from code_agent import config
from code_agent.kb import knowledge_graph, module_knowledge


def _write_knowledge_card(tmp_path, name, content):
    root = tmp_path / "docs" / "code-knowledge" / "marvel"
    root.mkdir(parents=True, exist_ok=True)
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


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
    assert msgs[0]["content"].rfind("对外回答格式") > msgs[0]["content"].rfind("已命中的模块知识卡")


def test_build_messages_injects_split_enemy_cards(monkeypatch, tmp_path):
    _write_knowledge_card(
        tmp_path,
        "enemy/enemy-skill-config.md",
        (
            "---\n"
            "type: Code Module\n"
            "title: Enemy 技能配置查表\n"
            "description: Enemy 技能缺失日志和 SkillListForEnemy 查表。\n"
            "repo: marvel\n"
            "tags: enemy, skill, config, 怪物, 技能, 配置\n"
            "symbols: SkillConfig::GetEnemySkillConfigX, SkillCore::InitEnemySkill, SkillListForEnemy\n"
            "logs: enemy conf skill, skill not find in conf\n"
            "updated_at: 2026-06-20\n"
            "---\n\n"
            "# Enemy 技能配置查表\n\n"
            "普通 Enemy 走 SkillListForEnemy；Spawn 走 SkillListForRole。\n"
        ),
    )
    _write_knowledge_card(
        tmp_path,
        "enemy/enemy-ai-agent.md",
        (
            "---\n"
            "type: Code Module\n"
            "title: AIEnemyAgent 怪物 AI\n"
            "description: AIID、UnitAITable、Sight 和 PatrolID 排查。\n"
            "repo: marvel\n"
            "tags: enemy, ai, 怪物\n"
            "symbols: AIEnemyAgent, AIUnitAgent\n"
            "updated_at: 2026-06-20\n"
            "---\n\n"
            "# AIEnemyAgent 怪物 AI\n\nAIID 选择 UnitAITable 或 SquadMemberAITable。\n"
        ),
    )
    monkeypatch.setattr(config, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(config, "CODE_REPOS", {})
    monkeypatch.setattr(config, "CODE_REPO_DEFAULT", "marvel")
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(tmp_path))
    monkeypatch.setattr(config, "LLM_PROMPT_CACHE", False)

    a = agent.CodeAgent(mode="plain")
    a.question = "GetEnemySkillConfigX enemy conf skill not find，怪物技能配置缺失怎么查？"
    msgs = a._build_messages(with_tools=True)

    assert "enemy/enemy-skill-config.md" in msgs[0]["content"]
    assert "Enemy 技能配置查表" in msgs[0]["content"]
    assert "SkillListForEnemy" in msgs[0]["content"]


def test_builtin_skill_editor_nodes_card_is_recallable():
    cards = knowledge_graph.load_cards("marvel", include_common=True)
    card = next(c for c in cards if c.id == "unit/skill-editor-nodes.md")
    assert card.title == "技能编辑器节点枚举"
    assert knowledge_graph.score_card(
        "技能编辑器节点 XBPNodeSys qteData resultData", card
    ) > 0


def test_answer_evidence_footer_uses_specific_card_fields(monkeypatch, tmp_path):
    _write_knowledge_card(
        tmp_path,
        "enemy/enemy-skill-config.md",
        (
            "---\n"
            "type: Code Module\n"
            "title: Enemy 技能配置查表\n"
            "tags: enemy, skill, config, 怪物\n"
            "resource: gameserver/tableload/skillconfig.cpp, gameserver/unit/skill/skillcore.cpp\n"
            "symbols: SkillConfig::GetEnemySkillConfigX, SkillCore::InitEnemySkill, SkillListForEnemy\n"
            "logs: enemy conf skill, not find in conf\n"
            "asserts: CHECK_COND\n"
            "---\n\n"
            "# Enemy 技能配置查表\n\nSkillListForEnemy 缺失会触发 not find in conf。\n"
        ),
    )
    monkeypatch.setattr(config, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(config, "CODE_REPOS", {})
    monkeypatch.setattr(config, "CODE_REPO_DEFAULT", "marvel")
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(tmp_path))

    a = agent.CodeAgent(mode="technical")
    a.question = "GetEnemySkillConfigX enemy conf skill not find in conf"
    footer = a._knowledge_evidence_footer("已有回答")

    assert "enemy/enemy-skill-config.md" in footer
    assert "gameserver/unit/skill/skillcore.cpp" in footer
    assert "SkillConfig::GetEnemySkillConfigX" in footer
    assert "not find in conf" in footer


def test_answer_evidence_footer_is_hidden_in_plain_mode(monkeypatch, tmp_path):
    _write_knowledge_card(
        tmp_path,
        "enemy/enemy-template-config.md",
        (
            "---\n"
            "title: Enemy 模板配置\n"
            "tags: enemy, config, 怪物\n"
            "resource: tableload/XEntityStatistics\n"
            "symbols: XEntityStatistics, UnitConf::InitFromTemplate\n"
            "---\n\n"
            "# Enemy 模板配置\n\n怪物模板配置。\n"
        ),
    )
    monkeypatch.setattr(config, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(config, "CODE_REPOS", {})
    monkeypatch.setattr(config, "CODE_REPO_DEFAULT", "marvel")
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(tmp_path))

    a = agent.CodeAgent(mode="plain")
    a.question = "怪物如何配置？"
    assert a._knowledge_evidence_footer("已有回答") == ""
