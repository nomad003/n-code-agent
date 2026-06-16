"""Tests for runtime diagnosis (方向 F): backtrace parsing + frame resolution."""
import config
import diagnose
import indexer
import pytest
import tools


# --- parsing (no index needed) ---------------------------------------------


def test_parse_gdb_frames():
    bt = (
        "Program terminated with signal SIGSEGV.\n"
        "#0  0x55ab in SceneMgr::Update (this=0x0, dt=0.016) at scene/scenemgr.cpp:142\n"
        "#1  0x55cd in GameLoop::tick() at game/loop.cpp:88\n"
        "#2  Update (x=5) at foo.cpp:10\n"
        "#3  0x7f11 in ?? ()\n"
        "(More stack frames follow...)\n"
    )
    frames = diagnose.parse_backtrace(bt)
    assert [f.num for f in frames] == [0, 1, 2, 3]
    assert frames[0].file == "scene/scenemgr.cpp" and frames[0].line == 142
    assert frames[1].func.startswith("GameLoop::tick")
    assert frames[3].func.startswith("??")  # unknown frame kept


def test_base_function():
    assert diagnose._base_function("SceneMgr::Update(int, float)") == "Update"
    assert diagnose._base_function("game::Foo<T>::bar() const") == "bar"
    assert diagnose._base_function("global_func") == "global_func"


def test_class_of():
    assert diagnose._class_of("SceneMgr::Update(int)") == "SceneMgr"
    assert diagnose._class_of("ns::Cls::method()") == "Cls"
    assert diagnose._class_of("global()") is None


def test_parse_skips_noise():
    assert diagnose.parse_backtrace("just some text\nno frames here") == []


# --- frame resolution against a real index ---------------------------------


@pytest.fixture
def indexed(tmp_path, monkeypatch):
    root = tmp_path / "src"
    (root / "scene").mkdir(parents=True)
    (root / "scene" / "scenemgr.h").write_text(
        "class SceneMgr {\n  void Update(float dt);\n};\n", encoding="utf-8"
    )
    (root / "other.cpp").write_text(
        "void Update(int x) {}\n", encoding="utf-8"  # same name, different place
    )
    db = tmp_path / "idx.db"
    indexer.build(root=str(root), db_path=str(db))
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(root))
    monkeypatch.setattr(config, "INDEX_DB_PATH", str(db))
    monkeypatch.setattr(config, "USE_INDEX", True)
    return root


def test_resolve_narrows_by_class(indexed):
    frames = diagnose.resolve_frames(
        diagnose.parse_backtrace("#0 SceneMgr::Update(float) at x.cpp:1")
    )
    # 'Update' exists twice; class name SceneMgr must narrow to scenemgr.h
    assert len(frames[0].candidates) == 1
    assert "scenemgr" in frames[0].candidates[0]["path"]


def test_resolve_bare_name_keeps_all(indexed):
    frames = diagnose.resolve_frames(
        diagnose.parse_backtrace("#0 Update(int) at x.cpp:1")
    )
    # No class qualifier -> both Update definitions are candidates
    assert len(frames[0].candidates) >= 2


def test_resolve_frame_tool(indexed):
    out = tools.resolve_frame("SceneMgr::Update(float)")
    assert "scenemgr.h" in out


# --- diagnose() orchestration (agent stubbed) ------------------------------


def test_diagnose_runs_agent(indexed, monkeypatch):
    import agent

    captured = {}

    def fake_answer(prompt, *, verbose=False):
        captured["prompt"] = prompt
        return "诊断结论：空指针解引用"

    monkeypatch.setattr(agent, "answer", fake_answer)
    result = diagnose.diagnose(
        "#0 SceneMgr::Update(float) at scene/scenemgr.cpp:2\n#1 main() at m.cpp:9"
    )
    assert result["answer"] == "诊断结论：空指针解引用"
    assert result["total_frames"] == 2
    assert result["resolved"] >= 1
    # the prompt must include the resolved candidate location
    assert "scenemgr.h" in captured["prompt"]


def test_diagnose_no_frames_still_answers(indexed, monkeypatch):
    import agent

    captured = {}

    def fake_answer(prompt, *, verbose=False):
        captured["prompt"] = prompt
        return "无法从该文本解析出栈帧"

    monkeypatch.setattr(agent, "answer", fake_answer)
    result = diagnose.diagnose("no frames at all")
    assert result["total_frames"] == 0
    # prompt should note that no frames were parsed
    assert "未能解析" in captured["prompt"]
