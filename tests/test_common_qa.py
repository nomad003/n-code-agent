"""Tests for maintained common Q&A cards."""
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
