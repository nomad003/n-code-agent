import json

from code_agent import config
from code_agent import trace_viewer
import pytest


def _write_trace(path, rows):
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )


def test_list_traces_newest_first(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LLM_TRACE_DIR", str(tmp_path))
    older = tmp_path / "20260101-000000-a.jsonl"
    newer = tmp_path / "20260102-000000-b.jsonl"
    _write_trace(
        older,
        [
            {"event": "request_start", "question": "旧问题", "mode": "plain", "backend": "custom"},
            {"event": "request_end"},
        ],
    )
    _write_trace(
        newer,
        [
            {"event": "request_start", "question": "新问题", "mode": "technical", "backend": "custom"},
            {"event": "llm_response"},
        ],
    )

    rows = trace_viewer.list_traces()
    assert [r["file"] for r in rows] == [newer.name, older.name]
    assert rows[0]["question"] == "新问题"
    assert rows[0]["last_event"] == "llm_response"


def test_read_trace(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LLM_TRACE_DIR", str(tmp_path))
    path = tmp_path / "trace.jsonl"
    _write_trace(
        path,
        [
            {"event": "request_start", "question": "Q", "mode": "plain", "backend": "custom", "model": "m"},
            {"event": "llm_request", "messages": [{"role": "user", "content": "Q"}]},
        ],
    )

    data = trace_viewer.read_trace(path.name)
    assert data["file"] == path.name
    assert data["question"] == "Q"
    assert data["rows"][1]["event"] == "llm_request"


def test_read_trace_rejects_path_escape(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LLM_TRACE_DIR", str(tmp_path))
    with pytest.raises(ValueError):
        trace_viewer.read_trace("../secret.jsonl")
