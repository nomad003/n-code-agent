"""Tests for offline code-knowledge evaluation."""
import json

from code_agent import config
from code_agent import knowledge_eval
from code_agent import main


def _write_knowledge_card(tmp_path, name, content):
    root = tmp_path / "docs" / "code-knowledge" / "marvel"
    root.mkdir(parents=True, exist_ok=True)
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_ranked_cards_hits_marvel_monster_card(monkeypatch, tmp_path):
    _write_knowledge_card(
        tmp_path,
        "monster-config.md",
        (
            "---\n"
            "title: 怪物配置与敌人技能配置链路\n"
            "tags: 怪物, monster, enemy, 技能, 配置\n"
            "symbols: SkillListForEnemy\n"
            "---\n\n"
            "# 怪物配置\n\n怪物技能在哪里配。\n"
        ),
    )
    monkeypatch.setattr(config, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(config, "CODE_REPOS", {})
    monkeypatch.setattr(config, "CODE_REPO_DEFAULT", "marvel")
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(tmp_path))

    ranked = knowledge_eval.ranked_cards(
        "怪物如何配置，怪物技能在哪里配？", repo="marvel"
    )

    assert ranked
    assert ranked[0]["id"] == "monster-config.md"


def test_ranked_cards_prefers_concrete_module_over_reference(monkeypatch, tmp_path):
    _write_knowledge_card(
        tmp_path,
        "enemy/index.md",
        (
            "---\n"
            "type: Reference\n"
            "title: Enemy 层索引\n"
            "tags: enemy, monster, skill, config, ai, spawn, 怪物, 技能, 配置\n"
            "symbols: CombatEnemy, SkillListForEnemy, AIEnemyAgent\n"
            "---\n\n"
            "# Enemy 层索引\n\nEnemy 技能、AI、配置、召唤物模块目录。\n"
        ),
    )
    _write_knowledge_card(
        tmp_path,
        "enemy/enemy-skill-config.md",
        (
            "---\n"
            "type: Code Module\n"
            "title: Enemy 技能配置查表\n"
            "tags: enemy, skill, config, 怪物, 技能, 配置\n"
            "symbols: SkillConfig::GetEnemySkillConfigX, SkillListForEnemy\n"
            "logs: enemy conf skill, skill not find in conf\n"
            "---\n\n"
            "# Enemy 技能配置查表\n\nSkillListForEnemy 是具体技能缺失排查入口。\n"
        ),
    )
    monkeypatch.setattr(config, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(config, "CODE_REPOS", {})
    monkeypatch.setattr(config, "CODE_REPO_DEFAULT", "marvel")
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(tmp_path))

    ranked = knowledge_eval.ranked_cards(
        "GetEnemySkillConfigX enemy conf skill not find，怪物技能配置缺失怎么查？",
        repo="marvel",
    )

    assert ranked[0]["id"] == "enemy/enemy-skill-config.md"


def test_evaluate_case_checks_fields_and_relations(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(config, "CODE_REPOS", {})
    monkeypatch.setattr(config, "CODE_REPO_DEFAULT", "marvel")
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(tmp_path / "target"))

    main.knowledge_save(
        main.KnowledgeSaveRequest(
            repo="marvel",
            name="a.md",
            content=(
                "---\n"
                "type: Code Module\n"
                "title: A\n"
                "description: A card\n"
                "repo: marvel\n"
                "tags: scene\n"
                "symbols: SceneMgr\n"
                "depends_on: b.md\n"
                "updated_at: 2026-06-19\n"
                "---\n\n# A\n\nSceneMgr 入口。\n"
            ),
        )
    )
    main.knowledge_save(
        main.KnowledgeSaveRequest(
            repo="marvel",
            name="b.md",
            content=(
                "---\n"
                "type: Code Module\n"
                "title: B\n"
                "description: B card\n"
                "repo: marvel\n"
                "tags: base\n"
                "updated_at: 2026-06-19\n"
                "---\n\n# B\n\nBase。\n"
            ),
        )
    )

    result = knowledge_eval.evaluate_case(
        {
            "repo": "marvel",
            "question": "SceneMgr 场景",
            "expect_top_card": "a.md",
            "expect_cards": ["a.md"],
            "expect_fields": [
                {"card": "a.md", "field": "symbols", "contains": ["SceneMgr"]},
                {"card": "a.md", "field": "body", "contains": ["SceneMgr"]},
            ],
            "expect_relations": [
                {"source": "a.md", "relation": "depends_on", "target": "b.md"}
            ],
        }
    )

    assert result["passed"] is True


def test_validate_repo_reports_broken_semantic_relation(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(config, "CODE_REPOS", {})
    monkeypatch.setattr(config, "CODE_REPO_DEFAULT", "marvel")
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(tmp_path / "target"))

    main.knowledge_save(
        main.KnowledgeSaveRequest(
            repo="marvel",
            name="a.md",
            content=(
                "---\n"
                "type: Code Module\n"
                "title: A\n"
                "description: A card\n"
                "repo: marvel\n"
                "depends_on: missing.md\n"
                "updated_at: 2026-06-19\n"
                "---\n\n# A\n"
            ),
        )
    )

    report = knowledge_eval.validate_repo("marvel")

    assert report["valid"] is False
    assert report["broken_relations"] == [
        {"source": "a.md", "relation": "depends_on", "target": "missing.md"}
    ]


def test_evaluate_summary(tmp_path, monkeypatch):
    _write_knowledge_card(
        tmp_path,
        "buff-framework.md",
        (
            "---\n"
            "title: Buff 框架\n"
            "tags: buff, BuffConfig, XBuffContainer\n"
            "symbols: BuffConfig, XBuffContainer\n"
            "---\n\n"
            "# Buff 框架\n\nBuff 配置字段在哪里解析。\n"
        ),
    )
    monkeypatch.setattr(config, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(config, "CODE_REPOS", {})
    monkeypatch.setattr(config, "CODE_REPO_DEFAULT", "marvel")
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(tmp_path))
    dataset = tmp_path / "knowledge.jsonl"
    dataset.write_text(
        json.dumps(
            {
                "repo": "marvel",
                "question": "Buff 配置字段在哪里解析？BuffConfig XBuffContainer",
                "expect_top_card": "buff-framework.md",
                "expect_cards": ["buff-framework.md"],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    summary = knowledge_eval.evaluate(str(dataset), validate=False)

    assert summary["total"] == 1
    assert summary["passed"] == 1
