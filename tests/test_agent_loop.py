"""Tests for the custom CodeAgent loop (offline — litellm is stubbed)."""
import types

import agent
import config
import pytest
from events import Action, Observation


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
