"""Tests for the offline index: build + query + tool integration."""
import config
import index_query
import indexer
import pytest
import tools


@pytest.fixture
def built_index(tmp_path, monkeypatch):
    """Build a small C++ index in a temp dir and point config at it."""
    root = tmp_path / "src"
    (root / "scene").mkdir(parents=True)
    (root / "scene" / "scenemgr.h").write_text(
        "class SceneMgr {\n"
        "public:\n"
        "    void load_scene(int id);\n"
        "};\n"
        "struct Vec3 { float x, y, z; };\n"
        "enum Color { RED, GREEN };\n",
        encoding="utf-8",
    )
    (root / "scene" / "scenemgr.cpp").write_text(
        '#include "scenemgr.h"\n'
        "void SceneMgr::load_scene(int id) { current_ = id; }\n",
        encoding="utf-8",
    )
    db = tmp_path / "idx.db"
    summary = indexer.build(root=str(root), db_path=str(db))

    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(root))
    monkeypatch.setattr(config, "INDEX_DB_PATH", str(db))
    monkeypatch.setattr(config, "USE_INDEX", True)
    return summary


# --- build -----------------------------------------------------------------


def test_build_summary(built_index):
    assert built_index["files"] == 2
    assert built_index["symbols"] >= 3  # class, struct, enum (+ method/def)


# --- index_query -----------------------------------------------------------


def test_query_available(built_index):
    assert index_query.available() is True


def test_find_symbol_exact(built_index):
    rows = index_query.find_symbol("SceneMgr")
    assert rows and any(r["kind"] == "class" and "scenemgr.h" in r["path"] for r in rows)


def test_find_symbol_struct_enum(built_index):
    assert any(r["kind"] == "struct" for r in index_query.find_symbol("Vec3"))
    assert any(r["kind"] == "enum" for r in index_query.find_symbol("Color"))


def test_find_symbol_miss_returns_empty_list(built_index):
    assert index_query.find_symbol("NoSuchSymbol") == []


def test_search_fts(built_index):
    hits = index_query.search_fts("load_scene")
    assert hits and any("scenemgr" in h["path"] for h in hits)


def test_meta_root(built_index, tmp_path):
    assert index_query.meta_root() == str(tmp_path / "src")


# --- no index → graceful None ----------------------------------------------


def test_query_unavailable_without_db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "INDEX_DB_PATH", str(tmp_path / "missing.db"))
    monkeypatch.setattr(config, "USE_INDEX", True)
    assert index_query.available() is False
    assert index_query.find_symbol("X") is None
    assert index_query.search_fts("X") is None


def test_disabled_via_flag(built_index, monkeypatch):
    monkeypatch.setattr(config, "USE_INDEX", False)
    assert index_query.available() is False
    assert index_query.find_symbol("SceneMgr") is None


# --- tools integration -----------------------------------------------------


def test_tool_find_symbol_uses_index(built_index):
    out = tools.find_symbol("SceneMgr")
    assert "scenemgr.h" in out and "[class]" in out


def test_tool_grep_uses_index_for_plain_text(built_index):
    out = tools.grep_code("load_scene")
    assert "scenemgr" in out


def test_tool_grep_regex_falls_back_to_live(built_index):
    # A regex pattern can't use FTS; must still work via the live scan.
    out = tools.grep_code(r"load_\w+")
    assert "load_scene" in out


# --- incremental update ----------------------------------------------------


def test_update_picks_up_new_file(built_index, tmp_path):
    root = tmp_path / "src"
    db = tmp_path / "idx.db"
    (root / "newmod.cpp").write_text("class NewThing {};\n", encoding="utf-8")
    summary = indexer.update(root=str(root), db_path=str(db))
    assert summary["added"] == 1
    assert any(r["kind"] == "class" for r in index_query.find_symbol("NewThing"))


def test_update_reindexes_changed_file(built_index, tmp_path):
    root = tmp_path / "src"
    db = tmp_path / "idx.db"
    # add a symbol to an existing file
    (root / "scene" / "scenemgr.h").write_text(
        "class SceneMgr { void Update(float dt); };\nstruct Added {};\n",
        encoding="utf-8",
    )
    summary = indexer.update(root=str(root), db_path=str(db))
    assert summary["changed"] == 1
    assert index_query.find_symbol("Added")  # new symbol now indexed


def test_update_removes_deleted_file(built_index, tmp_path):
    root = tmp_path / "src"
    db = tmp_path / "idx.db"
    (root / "scene" / "scenemgr.cpp").unlink()
    summary = indexer.update(root=str(root), db_path=str(db))
    assert summary["removed"] == 1


def test_update_noop_when_unchanged(built_index, tmp_path):
    summary = indexer.update(root=str(tmp_path / "src"), db_path=str(tmp_path / "idx.db"))
    assert summary == {**summary, "added": 0, "changed": 0, "removed": 0}


def test_update_without_db_does_full_build(tmp_path, monkeypatch):
    root = tmp_path / "src2"
    (root).mkdir()
    (root / "a.cpp").write_text("class A {};\n", encoding="utf-8")
    db = tmp_path / "fresh.db"
    summary = indexer.update(root=str(root), db_path=str(db))
    # fell back to build() → has "files"/"symbols" keys, not "added"
    assert "files" in summary and summary["files"] == 1


# --- entry short-circuit ---------------------------------------------------


def test_shortcut_answers_where_defined(built_index):
    import shortcut

    out = shortcut.try_answer("SceneMgr 定义在哪")
    assert out and "scenemgr.h" in out and "未经 LLM" in out


def test_shortcut_english(built_index):
    import shortcut

    out = shortcut.try_answer("where is SceneMgr defined")
    assert out and "scenemgr.h" in out


def test_shortcut_ignores_explanatory_question(built_index):
    import shortcut

    # "做什么" needs explanation → must NOT short-circuit
    assert shortcut.try_answer("SceneMgr 是做什么的") is None


def test_shortcut_unknown_symbol_falls_through(built_index):
    import shortcut

    assert shortcut.try_answer("NoSuchClass 定义在哪") is None


def test_shortcut_disabled(built_index, monkeypatch):
    import shortcut

    monkeypatch.setattr(config, "USE_INDEX", False)
    assert shortcut.try_answer("SceneMgr 定义在哪") is None


def test_answer_uses_shortcut(built_index, monkeypatch):
    import agent

    monkeypatch.setattr(config, "USE_SHORTCUT", True)
    monkeypatch.setattr(config, "AGENT_BACKEND", "custom")
    # if the shortcut fires, CodeAgent.run must never be called
    monkeypatch.setattr(agent.CodeAgent, "run",
                        lambda self, q: pytest.fail("LLM loop should be skipped"))
    out = agent.answer("SceneMgr 定义在哪")
    assert "scenemgr.h" in out
