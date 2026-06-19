"""Tests for the module knowledge maintenance UI/API helpers."""
import asyncio

import pytest

from code_agent import config
from code_agent import main


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
    assert "调查" in html and "复盘" in html and "知识" in html and "图谱" in html
    assert "markdown-preview" in html
    assert "brand-mark" not in html


def test_knowledge_graph_page_smoke():
    html = main.knowledge_graph_page().body.decode("utf-8")
    assert "Code Agent Workbench" in html
    assert "知识图谱" in html
    assert "graph-canvas" in html


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
            content="---\ntype: Code Module\ntitle: A\ntags: scene, level\n---\n\n# A\n\nSee [B](b.md).\n",
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
    assert any(e["source"] == "a.md" and e["target"] == "b.md" for e in graph["edges"])
    assert any(e["relation"] == "tagged_with" for e in graph["edges"])


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
