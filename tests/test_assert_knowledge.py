from code_agent import agent
from code_agent import assert_knowledge
from code_agent import config
from code_agent import indexer
from code_agent import tools


def test_build_catalog_extracts_neighbor_log_and_matches(monkeypatch, tmp_path):
    root = tmp_path / "src" / "gameserver"
    (root / "unit" / "skill").mkdir(parents=True)
    (root / "unit" / "skill" / "skillcore.cpp").write_text(
        "void SkillCore::InitEnemySkill() {\n"
        '  UnitLogErr(pUnit, "caster:%u skill:[%u %s] not find in conf", caster, skill, name);\n'
        "  CHECK_COND(false);\n"
        "}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(config, "CODE_REPOS", {})
    monkeypatch.setattr(config, "CODE_REPO_DEFAULT", "marvel")

    entries = assert_knowledge.build_catalog([("gameserver", str(root))], repo="marvel")
    assert len(entries) == 1
    entry = entries[0]
    assert entry.path == "gameserver/unit/skill/skillcore.cpp"
    assert entry.message == "caster:%u skill:[%u %s] not find in conf"
    assert entry.category == "config_or_table_missing"
    assert "配置/表数据缺失" in entry.problem

    assert_knowledge.write_catalog(entries, repo="marvel")
    hits = assert_knowledge.match(
        "InitEnemySkill(skillcore.cpp:3) Check cond: <false> failed skill not find in conf",
        repo="marvel",
    )
    assert hits
    assert hits[0][1].line == 3
    assert "not find in conf" in hits[0][1].message


def test_agent_prompt_injects_assert_playbook(monkeypatch, tmp_path):
    root = tmp_path / "src" / "gameserver"
    (root / "scene").mkdir(parents=True)
    (root / "scene" / "scene.cpp").write_text(
        "void Scene::load(int id) {\n"
        '  ASSERT_FALSE(id <= 0, "scene id invalid %d", id);\n'
        "}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(config, "CODE_REPOS", {})
    monkeypatch.setattr(config, "CODE_REPO_DEFAULT", "marvel")
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(root))
    monkeypatch.setattr(config, "LLM_PROMPT_CACHE", False)
    entries = assert_knowledge.build_catalog([("gameserver", str(root))], repo="marvel")
    assert_knowledge.write_catalog(entries, repo="marvel")

    a = agent.CodeAgent(mode="plain")
    a.question = "scene.cpp:2 ASSERT_FALSE scene id invalid 1001"
    msgs = a._build_messages(with_tools=True)
    system = msgs[0]["content"]
    assert "已命中的 Assert 知识" in system
    assert "scene id invalid" in system
    assert "排查/解决" in system


def test_find_assert_context_appends_structured_playbook(monkeypatch, tmp_path):
    root = tmp_path / "src"
    (root / "scene").mkdir(parents=True)
    (root / "scene" / "scenemgr.cpp").write_text(
        "void SceneMgr::load_scene(int id) {\n"
        '    ASSERT_FALSE(id <= 0, "scene id invalid %d", id);\n'
        "}\n",
        encoding="utf-8",
    )
    db = tmp_path / "idx.db"
    indexer.build(root=str(root), db_path=str(db))
    monkeypatch.setattr(config, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(config, "CODE_REPOS", {})
    monkeypatch.setattr(config, "CODE_REPO_DEFAULT", "marvel")
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(root))
    monkeypatch.setattr(config, "INDEX_DB_PATH", str(db))
    monkeypatch.setattr(config, "USE_INDEX", True)
    entries = assert_knowledge.build_catalog([("gameserver", str(root))], repo="marvel")
    assert_knowledge.write_catalog(entries, repo="marvel")

    out = tools.find_assert_context("scene id invalid 1001", context=2)
    assert "已命中的 Assert 知识" in out
    assert "对应问题" in out
    assert "ASSERT_FALSE" in out
    assert "context:" in out
