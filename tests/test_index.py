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
