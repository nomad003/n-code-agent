"""Tests for the sandboxed code-search tools (pure logic, no LLM)."""
from code_agent import config
import pytest
from code_agent import tools


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


def test_grep_with_context_shows_surrounding_lines(target_code):
    out = tools.grep_code("生命值", context=2)
    # Match line uses ':', context lines use '-' as the separator after the lineno.
    assert "scene/player.py:4: " in out
    assert "scene/player.py:2- " in out
    assert "scene/player.py:3- " in out


def test_grep_context_merges_adjacent_hunks(target_code):
    (target_code / "multi.txt").write_text(
        "a\nb\nHIT one\nc\nd\ne\nHIT two\nf\ng\n", encoding="utf-8"
    )
    out = tools.grep_code("HIT", context=2)
    # Windows [1..5] and [5..9] overlap on line 5 -> one merged hunk, no '--'.
    assert "--" not in out
    assert "multi.txt:3: HIT one" in out
    assert "multi.txt:7: HIT two" in out


def test_grep_context_separates_distant_hunks(target_code):
    (target_code / "far.txt").write_text(
        "a\nHIT one\nb\nc\nd\ne\nf\ng\nHIT two\nh\n", encoding="utf-8"
    )
    out = tools.grep_code("HIT", context=1)
    # Hunks [1..3] and [8..10] don't touch -> separator between them.
    assert "\n--\n" in out


def test_grep_files_mode_returns_paths_only(target_code):
    (target_code / "a.txt").write_text("HIT\nHIT\n", encoding="utf-8")
    (target_code / "b.txt").write_text("HIT\n", encoding="utf-8")
    out = tools.grep_code("HIT", output_mode="files")
    lines = [ln for ln in out.splitlines() if ln and not ln.startswith("...")]
    assert lines == sorted(lines)
    assert "a.txt" in lines and "b.txt" in lines
    # No "path:line:" content in files mode.
    assert ":" not in out.split("\n", 1)[0] or out.split("\n", 1)[0].endswith(".txt")


def test_grep_count_mode_ranks_by_frequency(target_code):
    (target_code / "hot.txt").write_text("HIT\n" * 5, encoding="utf-8")
    (target_code / "cold.txt").write_text("HIT\n", encoding="utf-8")
    out = tools.grep_code("HIT", output_mode="count")
    lines = out.splitlines()
    assert lines[0] == "hot.txt: 5"
    assert "cold.txt: 1" in lines


def test_grep_head_limit_truncates(target_code):
    for i in range(8):
        (target_code / f"f{i}.txt").write_text("HIT\n", encoding="utf-8")
    out = tools.grep_code("HIT", output_mode="files", head_limit=3)
    lines = [ln for ln in out.splitlines() if not ln.startswith("...")]
    assert len(lines) == 3
    assert "+5 more files" in out


def test_grep_rejects_invalid_output_mode(target_code):
    with pytest.raises(tools.ToolError):
        tools.grep_code("x", output_mode="bogus")


# --- glob ------------------------------------------------------------------


def test_glob_matches_basename_anywhere(target_code):
    out = tools.glob("**/player.py")
    assert "scene/player.py" in out.splitlines()


def test_glob_matches_root_segment(target_code):
    (target_code / "scene" / "a.lua").write_text("x", encoding="utf-8")
    (target_code / "scene" / "b.lua").write_text("x", encoding="utf-8")
    out = tools.glob("scene/*.lua")
    lines = out.splitlines()
    assert "scene/a.lua" in lines and "scene/b.lua" in lines


def test_glob_no_match(target_code):
    out = tools.glob("**/no-such-file.zzz")
    assert out.startswith("no files matching")


def test_glob_head_limit(target_code):
    for i in range(8):
        (target_code / f"t{i}.txt").write_text("x", encoding="utf-8")
    out = tools.glob("**/t*.txt", head_limit=3)
    lines = [ln for ln in out.splitlines() if not ln.startswith("...")]
    assert len(lines) == 3
    assert "+5 more files" in out


def test_glob_rejects_empty_pattern(target_code):
    with pytest.raises(tools.ToolError):
        tools.glob("")


def test_grep_falls_back_when_ripgrep_unavailable(target_code, monkeypatch):
    """When rg isn't on PATH the Python re scan must still answer."""
    monkeypatch.setattr(tools, "_RG_PATH", None)
    out = tools.grep_code("生命值")
    assert "scene/player.py:4:" in out


def test_grep_files_mode_uses_larger_raw_cap(target_code, monkeypatch):
    """files/count must scan beyond MAX_GREP_MATCHES so they don't truncate prematurely."""
    monkeypatch.setattr(config, "MAX_GREP_MATCHES", 5)   # tight content cap
    monkeypatch.setattr(config, "MAX_GREP_FILES", 50)    # loose enumeration cap
    # Create 20 files each with 3 hits → 60 raw matches; well past the content cap.
    for i in range(20):
        (target_code / f"hit_{i}.txt").write_text("HIT\n" * 3, encoding="utf-8")
    # content mode trips the small cap (5 matches across the first 2 files).
    content = tools.grep_code("HIT", output_mode="content")
    assert "truncated at 5 matches" in content
    # files mode scans up to 50 raw matches; >5 distinct files must surface,
    # proving the cap was raised for enumeration modes.
    files = tools.grep_code("HIT", output_mode="files")
    distinct = {ln for ln in files.splitlines() if ln.startswith("hit_")}
    assert len(distinct) > 5


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
    from code_agent import config

    # recall_knowledge is advertised only when the flywheel is on; with it
    # enabled, active_schemas() must exactly cover the registry.
    monkeypatch.setattr(config, "USE_KNOWLEDGE", True)
    schema_names = {s["function"]["name"] for s in tools.active_schemas()}
    assert schema_names == set(tools.TOOL_REGISTRY)
    # ...and recall_knowledge is hidden when the flywheel is off.
    monkeypatch.setattr(config, "USE_KNOWLEDGE", False)
    off_names = {s["function"]["name"] for s in tools.active_schemas()}
    assert "recall_knowledge" not in off_names
