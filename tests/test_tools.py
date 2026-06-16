"""Tests for the sandboxed code-search tools (pure logic, no LLM)."""
import config
import pytest
import tools


# --- path sandbox ----------------------------------------------------------


def test_resolve_allows_root_and_descendants(target_code):
    assert tools._resolve(".") == str(target_code)
    assert tools._resolve("scene/player.py") == str(target_code / "scene" / "player.py")


@pytest.mark.parametrize("bad", ["../outside.py", "../../etc/passwd", "scene/../../x"])
def test_resolve_rejects_escapes(target_code, bad):
    with pytest.raises(tools.ToolError):
        tools._resolve(bad)


def test_resolve_strips_leading_slash(target_code):
    # An absolute-looking path is treated as relative to the root, not as /etc/...
    assert tools._resolve("/scene/player.py") == str(
        target_code / "scene" / "player.py"
    )


# --- grep_code -------------------------------------------------------------


def test_grep_finds_match(target_code):
    out = tools.grep_code("生命值")
    assert "scene/player.py:4:" in out


def test_grep_no_match(target_code):
    assert tools.grep_code("nonexistent_xyz").startswith("no matches")


def test_grep_empty_pattern_raises(target_code):
    with pytest.raises(tools.ToolError):
        tools.grep_code("")


def test_grep_invalid_regex_raises(target_code):
    with pytest.raises(tools.ToolError):
        tools.grep_code("(unclosed")


def test_grep_respects_max_matches(target_code, monkeypatch):
    # Write a file with many matching lines, cap at 3.
    (target_code / "many.txt").write_text("hit\n" * 50, encoding="utf-8")
    monkeypatch.setattr(config, "MAX_GREP_MATCHES", 3)
    out = tools.grep_code("hit")
    assert "truncated at 3 matches" in out


# --- read_file -------------------------------------------------------------


def test_read_file_basic(target_code):
    out = tools.read_file("scene/player.py")
    assert "class Player" in out
    assert "1\tclass Player" in out  # line-numbered
    assert "of 4)" in out  # header reports total lines


def test_read_file_line_range(target_code):
    out = tools.read_file("scene/player.py", start=2, end=2)
    assert "def __init__" in out
    assert "class Player" not in out


def test_read_file_not_a_file(target_code):
    with pytest.raises(tools.ToolError):
        tools.read_file("scene")  # a directory


def test_read_file_past_eof(target_code):
    assert "past EOF" in tools.read_file("scene/player.py", start=999)


def test_read_file_truncates(target_code, monkeypatch):
    (target_code / "big.txt").write_text("x" * 5000, encoding="utf-8")
    monkeypatch.setattr(config, "MAX_READ_BYTES", 100)
    assert "truncated" in tools.read_file("big.txt")


# --- list_dir --------------------------------------------------------------


def test_list_dir_root(target_code):
    out = tools.list_dir(".")
    assert "scene/" in out  # dirs get a trailing slash


def test_list_dir_skips_hidden(target_code):
    assert ".hidden" not in tools.list_dir(".")


def test_list_dir_not_a_dir(target_code):
    with pytest.raises(tools.ToolError):
        tools.list_dir("scene/player.py")


# --- find_symbol -----------------------------------------------------------


def test_find_symbol_class(target_code):
    out = tools.find_symbol("SceneMgr")
    assert "scene/scene_mgr.py" in out
    assert "class SceneMgr" in out


def test_find_symbol_falls_back_to_plain_search(target_code):
    # "uid" has no def/class form; should fall back to a plain word search.
    out = tools.find_symbol("uid")
    assert "player.py" in out


# --- dispatch --------------------------------------------------------------


def test_dispatch_runs_tool(target_code):
    assert "scene/" in tools.dispatch("list_dir", {"path": "."})


def test_dispatch_unknown_tool(target_code):
    assert tools.dispatch("nope", {}).startswith("error: unknown tool")


def test_dispatch_tool_error_returned_as_string(target_code):
    # ToolError is caught and returned, not raised, so the loop can recover.
    out = tools.dispatch("read_file", {"path": "../escape"})
    assert out.startswith("error:")


def test_dispatch_bad_arguments(target_code):
    assert tools.dispatch("read_file", {"wrong": 1}).startswith("error:")


def test_tool_registry_matches_schemas(monkeypatch):
    import config

    # recall_knowledge is advertised only when the flywheel is on; with it
    # enabled, active_schemas() must exactly cover the registry.
    monkeypatch.setattr(config, "USE_KNOWLEDGE", True)
    schema_names = {s["function"]["name"] for s in tools.active_schemas()}
    assert schema_names == set(tools.TOOL_REGISTRY)
    # ...and recall_knowledge is hidden when the flywheel is off.
    monkeypatch.setattr(config, "USE_KNOWLEDGE", False)
    off_names = {s["function"]["name"] for s in tools.active_schemas()}
    assert "recall_knowledge" not in off_names
