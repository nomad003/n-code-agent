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


def test_base_function_operator_and_destructor():
    # operator overloads must not be truncated at their own parens/brackets
    assert diagnose._base_function("Fn::operator()(int)") == "operator()"
    assert diagnose._base_function("Buf::operator[](int)") == "operator[]"
    assert diagnose._base_function("A::operator==(const A&)") == "operator=="
    # destructors keep their leading ~
    assert diagnose._base_function("Foo::~Foo()") == "~Foo"
    # templated container method
    assert diagnose._base_function("std::vector<int>::push_back(int)") == "push_back"


def test_literal_runs_keeps_identifier_with_digits():
    # digits inside an identifier must NOT split the fixed text
    runs = diagnose._literal_runs("loading module abc123def now ok")
    assert any("abc123def" in r for r in runs)


def test_literal_runs_short_line_fallback():
    # no >=8 run, but the relaxed threshold still yields something
    runs = diagnose._literal_runs("init done 5")
    assert runs  # not silently empty


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


# --- log source lookup -----------------------------------------------------


def test_literal_runs_strips_values_and_prefix():
    runs = diagnose._literal_runs(
        "[2026-06-16 11:00:01] Buff 1024 cache data not found"
    )
    assert "cache data not found" in runs
    # timestamp and the number 1024 must be gone
    assert all("1024" not in r and "2026" not in r for r in runs)


def test_literal_runs_too_short():
    assert diagnose._literal_runs("err 5") == []  # nothing >= 8 chars


@pytest.fixture
def log_indexed(tmp_path, monkeypatch):
    root = tmp_path / "src"
    root.mkdir()
    (root / "buff.cpp").write_text(
        'void f() {\n'
        '    LogError("Buff %u cache data not found", id);\n'
        '    LogInfo("server stoped");\n'
        '}\n',
        encoding="utf-8",
    )
    db = tmp_path / "idx.db"
    indexer.build(root=str(root), db_path=str(db))
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(root))
    monkeypatch.setattr(config, "INDEX_DB_PATH", str(db))
    monkeypatch.setattr(config, "USE_INDEX", True)
    return root


def test_find_log_source_with_variable(log_indexed):
    hits = diagnose.find_log_source("Buff 4096 cache data not found")
    assert hits and any("buff.cpp" in h["path"] for h in hits)


def test_find_log_source_with_timestamp(log_indexed):
    hits = diagnose.find_log_source("[2026-06-16 11:00:01] server stoped")
    assert hits and any(h["line"] == 3 for h in hits)


def test_find_log_source_tool(log_indexed):
    out = tools.find_log_source("Buff 99 cache data not found")
    assert "buff.cpp" in out


def test_find_log_source_no_match(log_indexed):
    assert diagnose.find_log_source("totally unrelated banana text here") == []


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


def test_diagnose_with_plain_summary(indexed, monkeypatch):
    import agent

    calls = []

    def fake_answer(prompt, *, verbose=False):
        calls.append(prompt)
        # 1st call: technical analysis; 2nd: plain summary rewrite
        return "技术：空指针" if len(calls) == 1 else "服务器崩了，玩家掉线"

    monkeypatch.setattr(agent, "answer", fake_answer)
    result = diagnose.diagnose("#0 main() at m.cpp:1", with_plain=True)
    assert result["answer"] == "技术：空指针"
    assert result["plain"] == "服务器崩了，玩家掉线"
    assert len(calls) == 2  # technical + plain
    # the plain prompt is fed the technical answer
    assert "技术：空指针" in calls[1]


def test_diagnose_without_plain_has_no_plain_key(indexed, monkeypatch):
    import agent

    monkeypatch.setattr(agent, "answer", lambda p, *, verbose=False: "技术分析")
    result = diagnose.diagnose("#0 main() at m.cpp:1")
    assert "plain" not in result  # default: no extra LLM call
