"""Shared pytest fixtures.

Tests run entirely offline — no LLM, no network. The agent loop is exercised by
monkeypatching the per-backend answer functions; the tools are exercised against
a temporary throwaway codebase so they never touch the real target.
"""
import os
import sys

import pytest

# Make the project modules importable when pytest is run from the repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from code_agent import config  # noqa: E402


@pytest.fixture(autouse=True)
def isolate_llm_trace(tmp_path, monkeypatch):
    """Keep per-request trace files out of the repo during tests."""
    monkeypatch.setattr(config, "LLM_TRACE_ENABLED", True)
    monkeypatch.setattr(config, "LLM_TRACE_DIR", str(tmp_path / "llm-traces"))


@pytest.fixture
def target_code(tmp_path, monkeypatch):
    """Create a small temp codebase and point config.TARGET_CODE_PATH at it.

    Returns the root Path. tools.* read config.TARGET_CODE_PATH at call time,
    so monkeypatching the module attribute is enough.
    """
    root = tmp_path / "code"
    (root / "scene").mkdir(parents=True)
    (root / "scene" / "player.py").write_text(
        "class Player:\n"
        "    def __init__(self, uid):\n"
        "        self.uid = uid\n"
        "        self.hp = 100  # 玩家生命值\n",
        encoding="utf-8",
    )
    (root / "scene" / "scene_mgr.py").write_text(
        "class SceneMgr:\n"
        "    def load_scene(self, scene_id):\n"
        "        self.current = scene_id\n",
        encoding="utf-8",
    )
    # A nested dir and a hidden file (should be skipped by list_dir).
    (root / ".hidden").write_text("secret\n", encoding="utf-8")

    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(root))
    # Tool tests exercise the live-scan logic against this temp tree; disable the
    # offline index so they never accidentally hit a real prebuilt index DB.
    monkeypatch.setattr(config, "USE_INDEX", False)
    return root
