"""Tests for the custom CodeAgent loop (offline — litellm is stubbed)."""
import json
import types
from pathlib import Path

from code_agent.core import agent
from code_agent import config
import pytest
from code_agent.core.events import Action, Observation


# --- helpers to fake litellm responses -------------------------------------


def _msg(content=None, tool_calls=None):
    """Build an object shaped like litellm's response.choices[0].message."""
    m = types.SimpleNamespace(content=content, tool_calls=tool_calls)
    m.model_dump = lambda: {
        "role": "assistant",
        "content": content,
        "tool_calls": [
            {"id": tc.id, "type": "function",
             "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in (tool_calls or [])
        ],
    }
    return m


def _tool_call(call_id, name, arguments):
    return types.SimpleNamespace(
        id=call_id,
        function=types.SimpleNamespace(name=name, arguments=arguments),
    )


def _response(message):
    return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])


@pytest.fixture
def stub_llm(monkeypatch):
    """Drive the loop with a scripted list of assistant messages."""
    def install(messages, target_path):
        monkeypatch.setattr(config, "TARGET_CODE_PATH", target_path)
        monkeypatch.setattr(config, "LLM_API_KEY", "sk-test")
        seq = iter(messages)
        calls = {"n": 0}

        def fake_completion(**kwargs):
            calls["n"] += 1
            return _response(next(seq))

        monkeypatch.setattr(agent.litellm, "completion", fake_completion)
        return calls

    return install


# --- direct answer (no tools) ----------------------------------------------


def test_direct_answer(stub_llm, tmp_path):
    stub_llm([_msg(content="直接回答")], str(tmp_path))
    assert agent.CodeAgent().run("问题") == "直接回答"


# --- one tool call then answer ---------------------------------------------


def test_tool_call_then_answer(stub_llm, tmp_path):
    (tmp_path / "a.py").write_text("class Foo: pass\n", encoding="utf-8")
    calls = stub_llm(
        [
            _msg(tool_calls=[_tool_call("c1", "find_symbol", '{"name": "Foo"}')]),
            _msg(content="Foo 在 a.py"),
        ],
        str(tmp_path),
    )
    a = agent.CodeAgent()
    assert a.run("Foo 在哪") == "Foo 在 a.py"
    assert calls["n"] == 2
    # history: one Action + one Observation
    assert isinstance(a.history[0], Action)
    assert isinstance(a.history[1], Observation)
    assert "a.py" in a.history[1].content


def test_answer_writes_per_request_llm_trace(stub_llm, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "USE_SHORTCUT", False)
    trace_dir = tmp_path / "traces"
    monkeypatch.setattr(config, "LLM_TRACE_DIR", str(trace_dir))
    (tmp_path / "a.py").write_text("class Foo: pass\n", encoding="utf-8")
    stub_llm(
        [
            _msg(tool_calls=[_tool_call("c1", "find_symbol", '{"name": "Foo"}')]),
            _msg(content="Foo 在 a.py"),
        ],
        str(tmp_path),
    )

    assert agent.answer("Foo 在哪") == "Foo 在 a.py"

    files = list(Path(config.LLM_TRACE_DIR).glob("*.jsonl"))
    assert len(files) == 1
    rows = [json.loads(line) for line in files[0].read_text(encoding="utf-8").splitlines()]
    events = [r["event"] for r in rows]
    assert events[0] == "request_start"
    assert events.count("llm_request") == 2
    assert events.count("llm_response") == 2
    assert "tool_result" in events
    assert events[-1] == "request_end"
    assert "knowledge_context_injected" in events
    first_request = next(r for r in rows if r["event"] == "llm_request")
    assert first_request["messages"][0]["role"] == "system"
    assert first_request["messages"][1] == {"role": "user", "content": "Foo 在哪"}
    tool_row = next(r for r in rows if r["event"] == "tool_result")
    assert tool_row["name"] == "find_symbol"
    assert "a.py" in tool_row["result"]


def test_build_messages_traces_knowledge_context(tmp_path, monkeypatch):
    root = tmp_path / "docs" / "code-knowledge" / "marvel"
    root.mkdir(parents=True)
    (root / "monster-config.md").write_text(
        (
            "---\n"
            "title: 怪物配置\n"
            "tags: 怪物, enemy, config\n"
            "symbols: CombatEnemy\n"
            "---\n\n"
            "# 怪物配置\n\nCombatEnemy 使用 XEntityStatistics。\n"
        ),
        encoding="utf-8",
    )
    trace_dir = tmp_path / "traces"
    monkeypatch.setattr(config, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(tmp_path))
    monkeypatch.setattr(config, "CODE_REPOS", {})
    monkeypatch.setattr(config, "CODE_REPO_DEFAULT", "marvel")
    monkeypatch.setattr(config, "LLM_TRACE_DIR", str(trace_dir))
    monkeypatch.setattr(config, "LLM_TRACE_ENABLED", True)
    monkeypatch.setattr(config, "LLM_PROMPT_CACHE", False)
    monkeypatch.setattr(config, "CODE_KNOWLEDGE_MAP_ENABLED", True)

    trace = agent.llm_trace.LLMTrace(
        question="怪物配置怎么配", mode="plain", backend="custom"
    )
    a = agent.CodeAgent(mode="plain", trace=trace)
    a.question = "怪物配置怎么配"
    messages = a._build_messages(with_tools=True)

    assert "代码知识库地图" in messages[0]["content"]
    assert "已命中的模块知识卡" in messages[0]["content"]
    rows = [
        json.loads(line)
        for line in Path(trace.path).read_text(encoding="utf-8").splitlines()
    ]
    event = next(r for r in rows if r["event"] == "knowledge_context_injected")
    assert event["code_knowledge_map_injected"] is True
    assert event["module_cards_injected"] is True
    assert "monster-config.md" in event["code_knowledge_map_cards"]
    assert any(path.endswith("monster-config.md") for path in event["module_cards"])
    blocks = {block["key"]: block for block in event["blocks"]}
    assert blocks["base_prompt"]["injected"] is True
    assert blocks["intent_prompt"]["injected"] is True
    assert blocks["knowledge_graph"]["injected"] is True
    assert blocks["module_cards"]["injected"] is True
    assert blocks["output_mode"]["injected"] is True
    assert "代码知识库地图" in blocks["knowledge_graph"]["content"]
    assert "已命中的模块知识卡" in blocks["module_cards"]["content"]


# --- message building keeps pairing ----------------------------------------


def test_build_messages_pairs_tool_results(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(tmp_path))
    a = agent.CodeAgent()
    a.question = "Q"
    assistant_msg = {"role": "assistant", "tool_calls": [{"id": "c1"}]}
    a.history = [
        Action("c1", "list_dir", "{}", assistant_message=assistant_msg),
        Observation("c1", "list_dir", "result text"),
    ]
    msgs = a._build_messages(with_tools=True)
    assert msgs[0]["role"] == "system"
    assert msgs[1] == {"role": "user", "content": "Q"}
    assert msgs[2] is assistant_msg                     # assistant turn once
    assert msgs[3]["role"] == "tool" and msgs[3]["tool_call_id"] == "c1"


def test_build_messages_injects_question_intent(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(tmp_path))
    monkeypatch.setattr(config, "LLM_PROMPT_CACHE", False)
    a = agent.CodeAgent()
    a.question = "[ERROR] ASSERT_FALSE player id invalid 1001"
    msgs = a._build_messages(with_tools=True)
    assert "当前问题类型：宕机/错误日志分析" in msgs[0]["content"]
    assert "find_assert_context" in msgs[0]["content"]


def test_build_messages_dedupes_multi_call_assistant(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(tmp_path))
    a = agent.CodeAgent()
    a.question = "Q"
    shared = {"role": "assistant", "tool_calls": [{"id": "c1"}, {"id": "c2"}]}
    a.history = [
        Action("c1", "list_dir", "{}", assistant_message=shared),
        Observation("c1", "list_dir", "r1"),
        Action("c2", "grep_code", '{"pattern":"x"}', assistant_message=shared),
        Observation("c2", "grep_code", "r2"),
    ]
    msgs = a._build_messages(with_tools=True)
    # the shared assistant message must appear exactly once
    assert sum(1 for m in msgs if m is shared) == 1
    # both tool results present
    tool_ids = [m["tool_call_id"] for m in msgs if m.get("role") == "tool"]
    assert tool_ids == ["c1", "c2"]


# --- stuck detection -------------------------------------------------------


def test_stuck_after_repeated_identical_calls(stub_llm, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "STUCK_REPEAT_THRESHOLD", 3)
    monkeypatch.setattr(config, "MAX_ITERATIONS", 20)
    same = lambda: _msg(tool_calls=[_tool_call("c", "grep_code", '{"pattern":"zzz"}')])
    # 3 identical tool-call turns, then a final wrap-up answer
    calls = stub_llm([same(), same(), same(), _msg(content="尽力回答")], str(tmp_path))
    a = agent.CodeAgent()
    assert a.run("问题") == "尽力回答"
    # 3 tool rounds + 1 final wrap-up = 4 llm calls (did NOT run all 20)
    assert calls["n"] == 4


def test_stuck_same_pattern_varying_path(stub_llm, tmp_path, monkeypatch):
    """grep_code re-issued with the same pattern but a tweaked path/mode still stucks."""
    monkeypatch.setattr(config, "STUCK_REPEAT_THRESHOLD", 3)
    monkeypatch.setattr(config, "MAX_ITERATIONS", 20)
    turns = [
        _msg(tool_calls=[_tool_call("c1", "grep_code", '{"pattern":"zzz","path":"a"}')]),
        _msg(tool_calls=[_tool_call("c2", "grep_code", '{"pattern":"zzz","path":"b"}')]),
        _msg(tool_calls=[_tool_call("c3", "grep_code", '{"pattern":"zzz","output_mode":"files"}')]),
        _msg(content="尽力回答"),
    ]
    calls = stub_llm(turns, str(tmp_path))
    assert agent.CodeAgent().run("问题") == "尽力回答"
    assert calls["n"] == 4  # 3 stuck rounds + wrap-up


def test_stuck_all_recent_errors(stub_llm, tmp_path, monkeypatch):
    """If the last N observations are all errors, bail out."""
    monkeypatch.setattr(config, "STUCK_REPEAT_THRESHOLD", 3)
    monkeypatch.setattr(config, "MAX_ITERATIONS", 20)
    # Each call points at a different bogus path so action_key/primary_key all
    # differ — only the all-errors rule should fire.
    turns = [
        _msg(tool_calls=[_tool_call(f"c{i}", "read_file",
            f'{{"path":"nope_{i}.txt","start":1,"end":5}}')])
        for i in range(3)
    ] + [_msg(content="尽力回答")]
    calls = stub_llm(turns, str(tmp_path))
    a = agent.CodeAgent()
    assert a.run("问题") == "尽力回答"
    assert calls["n"] == 4
    # Confirm the observations actually were errors (otherwise the test is moot).
    obs = [e for e in a.history if isinstance(e, Observation)]
    assert len(obs) == 3 and all(o.is_error for o in obs)


def test_stuck_disabled(stub_llm, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "STUCK_REPEAT_THRESHOLD", 0)
    a = agent.CodeAgent()
    assert a._is_stuck() is False  # never stuck when disabled


# --- iteration cap ---------------------------------------------------------


def _obs_history(n):
    """n Action/Observation pairs with distinct, sizeable observation content."""
    hist = []
    for i in range(n):
        am = {"role": "assistant", "tool_calls": [{"id": f"c{i}"}]}
        hist.append(Action(f"c{i}", "grep_code", f'{{"pattern":"p{i}"}}', assistant_message=am))
        hist.append(Observation(f"c{i}", "grep_code", f"完整输出-{i}\n" + "x" * 500))
    return hist


def test_masking_keeps_only_recent(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(tmp_path))
    monkeypatch.setattr(config, "OBS_KEEP_FULL", 2)
    a = agent.CodeAgent()
    a.question = "Q"
    a.history = _obs_history(5)  # 5 observations, keep last 2 full
    tool_msgs = [m for m in a._build_messages(with_tools=True) if m.get("role") == "tool"]
    assert len(tool_msgs) == 5
    # first 3 masked, last 2 full
    assert all(m["content"].startswith("[省略") for m in tool_msgs[:3])
    assert tool_msgs[3]["content"].startswith("完整输出-3")
    assert tool_msgs[4]["content"].startswith("完整输出-4")


def test_masking_disabled_keeps_all(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(tmp_path))
    monkeypatch.setattr(config, "OBS_KEEP_FULL", 0)
    a = agent.CodeAgent()
    a.question = "Q"
    a.history = _obs_history(4)
    tool_msgs = [m for m in a._build_messages(with_tools=True) if m.get("role") == "tool"]
    assert all(not m["content"].startswith("[省略") for m in tool_msgs)


def test_masking_under_threshold_no_mask(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "TARGET_CODE_PATH", str(tmp_path))
    monkeypatch.setattr(config, "OBS_KEEP_FULL", 6)
    a = agent.CodeAgent()
    a.question = "Q"
    a.history = _obs_history(3)  # fewer than keep -> nothing masked
    tool_msgs = [m for m in a._build_messages(with_tools=True) if m.get("role") == "tool"]
    assert all(not m["content"].startswith("[省略") for m in tool_msgs)


def test_iteration_cap_triggers_final_answer(stub_llm, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "MAX_ITERATIONS", 2)
    monkeypatch.setattr(config, "STUCK_REPEAT_THRESHOLD", 0)  # don't short-circuit
    # always asks for a (varying) tool call, never answers directly
    msgs = [
        _msg(tool_calls=[_tool_call("c", "grep_code", f'{{"pattern":"p{i}"}}')])
        for i in range(2)
    ] + [_msg(content="基于现有信息的回答")]
    calls = stub_llm(msgs, str(tmp_path))
    assert agent.CodeAgent().run("问题") == "基于现有信息的回答"
    assert calls["n"] == 3  # 2 loop iterations + 1 final wrap-up


def test_iteration_cap_reuses_substantial_assistant_text(stub_llm, tmp_path, monkeypatch):
    """When the last turn already has answer-shaped text, skip the wrap-up call."""
    monkeypatch.setattr(config, "MAX_ITERATIONS", 2)
    monkeypatch.setattr(config, "STUCK_REPEAT_THRESHOLD", 0)
    substantive = "基于已收集的证据：玩家血量字段是 hp，定义在 player.py 第 4 行。" * 4
    msgs = [
        _msg(
            content=substantive,
            tool_calls=[_tool_call("c", "grep_code", f'{{"pattern":"p{i}"}}')],
        )
        for i in range(2)
    ]
    calls = stub_llm(msgs, str(tmp_path))
    out = agent.CodeAgent().run("问题")
    assert out == substantive.strip()
    assert calls["n"] == 2  # no wrap-up call


def test_iteration_cap_ignores_short_narration(stub_llm, tmp_path, monkeypatch):
    """Short 'let me check X' narration shouldn't bypass the wrap-up call."""
    monkeypatch.setattr(config, "MAX_ITERATIONS", 2)
    monkeypatch.setattr(config, "STUCK_REPEAT_THRESHOLD", 0)
    msgs = [
        _msg(content="继续检索。", tool_calls=[_tool_call("c1", "grep_code", '{"pattern":"x"}')]),
        _msg(content="还需要确认。", tool_calls=[_tool_call("c2", "grep_code", '{"pattern":"y"}')]),
        _msg(content="正式答案"),
    ]
    calls = stub_llm(msgs, str(tmp_path))
    assert agent.CodeAgent().run("问题") == "正式答案"
    assert calls["n"] == 3  # wrap-up still happens — narration was too short


def test_system_message_gets_cache_control_when_enabled(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LLM_PROMPT_CACHE", True)
    a = agent.CodeAgent()
    a.question = "Q"
    msgs = a._build_messages(with_tools=True)
    sys_content = msgs[0]["content"]
    assert isinstance(sys_content, list)
    assert sys_content[0]["cache_control"] == {"type": "ephemeral"}


def test_system_message_is_plain_string_when_cache_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LLM_PROMPT_CACHE", False)
    a = agent.CodeAgent()
    a.question = "Q"
    msgs = a._build_messages(with_tools=True)
    assert isinstance(msgs[0]["content"], str)
