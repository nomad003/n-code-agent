"""Tests for the module knowledge maintenance UI/API helpers."""
import asyncio
from pathlib import Path

import pytest

from code_agent import config
from server import app as main


@pytest.fixture
def knowledge_env(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(config, "CODE_REPOS", {})
    monkeypatch.setattr(config, "CODE_REPO_DEFAULT", "marvel")
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(tmp_path / "target"))
    return tmp_path


def test_knowledge_page_smoke():
    html = main.knowledge_page().body.decode("utf-8")
    assert "Code Agent Workbench" in html
    assert "/knowledge/api" in html
    assert "/knowledge/graph" in html
    assert "通用问答集" in html
    assert "调查" in html and "复盘" in html and "知识" in html and "图谱" in html
    assert "theme-toggle" in html
    assert "markdown-preview" in html
    assert "answer-preview" in html
    assert '<option value="">自动识别</option>' in html
    assert "knowledge-tree" in html
    assert "showCardPreview" in html
    assert "brand-mark" not in html
    app_js = Path("frontend/static/app.js").read_text(encoding="utf-8")
    assert "renderKnowledgeDiagrams" in app_js
    assert "renderedAskAnswer" in app_js
    assert "renderedCommonQaAnswer" in app_js
    assert "/knowledge/api/common-qa" in app_js
    assert "loadCommonQa" in app_js
    assert "isCommonQaCard" in app_js
    assert 'this.view === "ask"' in app_js
    assert "canRenderAsk" in app_js
    assert "等待提交问题。" in app_js
    assert "code-agent.askWorkspace" in app_js
    assert "readAskWorkspace" in app_js
    assert "saveAskWorkspace" in app_js
    assert "persistAskWorkspace" in app_js
    assert "selectedExists" in app_js
    assert 'question_type: ""' in app_js
    assert 'curateQuestionType: ""' in app_js
    assert "querySelectorAll('.markdown-preview .diagram-card" in app_js
    assert "modeOptions" in app_js
    assert "preferredKnowledgeQaMode" in app_js
    app_css = Path("frontend/static/app.css").read_text(encoding="utf-8")
    assert "grid-template-columns: repeat(3" in app_css
    assert "commonqa-stack" in app_css
    assert "commonqa-sidebar" in app_css
    assert "commonqa-picker" not in app_css
    assert "qa-workbench" in html
    assert "qa-flow" in html
    assert "追问并生成草稿" in html
    assert "保存后会进入模块卡片列表" in html
    assert "qa-meta-fields" in app_css
    assert "qa-compose" in app_css
    assert "knowledgeCardRows" in app_js
    assert "toggleKnowledgeTree" in app_js
    assert "encodePath(name)" in app_js
    assert "mermaid.min.js" in app_js
    assert "/static/vendor/vis-network.min.js" in app_js
    assert "diagram-card" in app_js
    assert "markdown-table-wrap" in app_js
    assert Path("frontend/static/vendor/vue.global.prod.js").exists()
    assert Path("frontend/static/vendor/vis-network.min.js").exists()
    assert Path("frontend/static/vendor/mermaid.min.js").exists()


def test_knowledge_graph_page_smoke():
    html = main.knowledge_graph_page().body.decode("utf-8")
    assert "Code Agent Workbench" in html
    assert "知识图谱" in html
    assert "graph-canvas" in html
    assert "关系说明" in html


def test_trace_page_smoke():
    html = main.llm_traces_page().body.decode("utf-8")
    assert "调用复盘" in html
    assert "trace-question-card" in html
    assert "Round 明细" in html
    assert "本轮原始事件" in html
    assert '<script src="https://unpkg.com' not in html
    app_js = Path("frontend/static/app.js").read_text(encoding="utf-8")
    assert "renderTraceFallback" in app_js
    assert "/static/vendor/vue.global.prod.js" in app_js


def test_knowledge_save_list_read(knowledge_env):
    req = main.KnowledgeSaveRequest(
        repo="marvel",
        name="monster-config.md",
        content="---\ntitle: 怪物配置\ntags: 怪物, 技能\n---\n\n# 怪物配置\n",
    )
    assert main.knowledge_save(req)["saved"] is True

    listed = main.knowledge_list("marvel")
    assert listed["cards"][0]["name"] == "monster-config.md"
    assert listed["cards"][0]["title"] == "怪物配置"
    assert "怪物" in listed["cards"][0]["tags"]
    assert listed["cards"][0]["segments"] == ["monster-config.md"]
    assert listed["cards"][0]["group"] == ""
    assert listed["cards"][0]["depth"] == 0

    read = main.knowledge_read("marvel", "monster-config.md")
    assert "# 怪物配置" in read["content"]
    assert read["meta"]["title"] == "怪物配置"


def test_knowledge_rejects_path_escape(knowledge_env):
    with pytest.raises(main.HTTPException):
        main.knowledge_read("marvel", "../escape.md")


def test_knowledge_graph_links_and_tags(knowledge_env):
    main.knowledge_save(
        main.KnowledgeSaveRequest(
            repo="marvel",
            name="a.md",
            content=(
                "---\n"
                "type: Code Module\n"
                "title: A\n"
                "tags: scene, level\n"
                "symbols: SceneMgr, LevelMgr\n"
                "logs: SceneErr\n"
                "asserts: CHECK_COND\n"
                "question_types: outage_log, feature_impl\n"
                "resource: gameserver/scene\n"
                "depends_on: b.md\n"
                "supplements: b.md\n"
                "part_of: b.md\n"
                "---\n\n# A\n\nSee [B](b.md).\n"
            ),
        )
    )
    main.knowledge_save(
        main.KnowledgeSaveRequest(
            repo="marvel",
            name="b.md",
            content="---\ntype: Code Module\ntitle: B\ntags: level\n---\n\n# B\n",
        )
    )
    graph = main.knowledge_graph("marvel")
    node_ids = {n["id"] for n in graph["nodes"]}
    assert {"a.md", "b.md", "tag:scene", "tag:level"} <= node_ids
    assert "symbol:SceneMgr" in node_ids
    assert "log:SceneErr" in node_ids
    assert "assert:CHECK_COND" in node_ids
    assert "question_type:outage_log" in node_ids
    assert "resource:gameserver/scene" in node_ids
    assert any(e["source"] == "a.md" and e["target"] == "b.md" for e in graph["edges"])
    assert any(e["relation"] == "tagged_with" for e in graph["edges"])
    assert any(e["relation"] == "owns_symbol" for e in graph["edges"])
    assert any(e["relation"] == "emits_log" for e in graph["edges"])
    assert any(e["relation"] == "checks_assert" for e in graph["edges"])
    assert any(e["relation"] == "answers_question_type" for e in graph["edges"])
    assert any(e["relation"] == "documents_resource" for e in graph["edges"])
    assert any(
        e["relation"] == "depends_on" and e["target"] == "b.md"
        for e in graph["edges"]
    )
    assert any(
        e["relation"] == "supplements" and e["target"] == "b.md"
        for e in graph["edges"]
    )
    assert any(
        e["relation"] == "part_of" and e["target"] == "b.md"
        for e in graph["edges"]
    )
    relations = {item["id"]: item for item in graph["relations"]}
    assert relations["links_to"]["label"] == "内部链接"
    assert relations["tagged_with"]["label"] == "标签归类"
    assert relations["owns_symbol"]["label"] == "关键符号"
    assert relations["emits_log"]["label"] == "日志线索"
    assert relations["depends_on"]["label"] == "依赖"
    assert relations["supplements"]["label"] == "补充"
    assert relations["part_of"]["label"] == "组成/从属"
    assert "Markdown" in relations["links_to"]["description"]


def test_knowledge_nested_card_path(knowledge_env):
    saved = main.knowledge_save(
        main.KnowledgeSaveRequest(
            repo="marvel",
            name="gameserver/scene.md",
            content="---\ntitle: 场景子目录\ntags: scene\n---\n\n# 场景子目录\n",
        )
    )
    assert saved["name"] == "gameserver/scene.md"
    listed = main.knowledge_list("marvel")
    assert listed["cards"][0]["name"] == "gameserver/scene.md"
    assert listed["cards"][0]["segments"] == ["gameserver", "scene.md"]
    assert listed["cards"][0]["group"] == "gameserver"
    assert listed["cards"][0]["depth"] == 1
    read = main.knowledge_read("marvel", "gameserver/scene.md")
    assert read["name"] == "gameserver/scene.md"
    assert read["title"] == "场景子目录"


def test_knowledge_graph_resolves_relative_semantic_relation(knowledge_env):
    main.knowledge_save(
        main.KnowledgeSaveRequest(
            repo="marvel",
            name="gameserver/scene.md",
            content=(
                "---\n"
                "title: 场景子目录\n"
                "depends_on: ../common/base.md\n"
                "---\n\n# 场景子目录\n"
            ),
        )
    )
    main.knowledge_save(
        main.KnowledgeSaveRequest(
            repo="marvel",
            name="common/base.md",
            content="---\ntitle: 基础卡\n---\n\n# 基础卡\n",
        )
    )
    graph = main.knowledge_graph("marvel")
    assert any(
        e["source"] == "gameserver/scene.md"
        and e["target"] == "common/base.md"
        and e["relation"] == "depends_on"
        for e in graph["edges"]
    )


def test_knowledge_precipitate_creates_card(knowledge_env):
    req = main.KnowledgePrecipitateRequest(
        repo="marvel",
        name="qa-test.md",
        title="问答沉淀测试",
        question="SceneMgr 是什么？",
        answer="SceneMgr 管理场景。",
        tags="scene, qa",
        refs=["gameserver/scene/scenemgr.cpp"],
    )
    saved = main.knowledge_precipitate(req)
    assert saved["saved"] is True
    read = main.knowledge_read("marvel", "qa-test.md")
    assert read["meta"]["type"] == "Code Playbook"
    assert "SceneMgr 管理场景" in read["content"]


def test_knowledge_qa_ask_calls_agent(knowledge_env, monkeypatch):
    captured = {}
    monkeypatch.setattr(config, "AGENT_ALLOWED_MODES", ("plain", "technical"))

    def fake_answer(question, *, mode="plain", repo=None, question_type=None, **_kwargs):
        captured.update(
            {
                "question": question,
                "mode": mode,
                "repo": repo,
                "question_type": question_type,
            }
        )
        return "模型回答"

    monkeypatch.setattr(main.agent, "answer", fake_answer)
    req = main.KnowledgeCurateAskRequest(
        repo="marvel",
        question="场景如何创建？",
        mode="technical",
        question_type="feature_impl",
    )
    res = asyncio.run(main.knowledge_qa_ask(req))
    assert res["answer"] == "模型回答"
    assert captured == {
        "question": "场景如何创建？",
        "mode": "technical",
        "repo": "marvel",
        "question_type": "feature_impl",
    }


def test_knowledge_common_qa_api_lists_curated_cards(knowledge_env):
    root = knowledge_env / "docs" / "code-knowledge" / "marvel" / "common-qa"
    root.mkdir(parents=True)
    (root / "monster-config.md").write_text(
        (
            "---\n"
            "type: Common QA\n"
            "title: 怪物配置\n"
            "questions: 怪物配置, 怪物怎么配置\n"
            "aliases: monster config\n"
            "tags: qa, monster\n"
            "---\n\n"
            "# 怪物配置\n\n编辑好的答案。\n"
        ),
        encoding="utf-8",
    )

    res = main.knowledge_common_qa("marvel")
    assert res["repo"] == "marvel"
    assert res["items"][0]["name"] == "common-qa/monster-config.md"
    assert res["items"][0]["title"] == "怪物配置"
    assert "怪物怎么配置" in res["items"][0]["questions"]
    assert "编辑好的答案" in res["items"][0]["answer"]
