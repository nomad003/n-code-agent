"""Per-request LLM interaction trace logging.

Trace files are JSONL so they can be tailed while a long request is running and
parsed later without loading the whole file. Logging is best-effort: failures
must never break the user request.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Any

from . import config


def _now() -> str:
    return datetime.now().isoformat(timespec="milliseconds")


def _request_id() -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    return f"{stamp}-{uuid.uuid4().hex[:8]}"


class LLMTrace:
    """Append-only JSONL trace for one external agent request."""

    def __init__(self, *, question: str, mode: str, backend: str):
        self.enabled = bool(config.LLM_TRACE_ENABLED)
        self.request_id = _request_id()
        self.path = os.path.join(config.LLM_TRACE_DIR, f"{self.request_id}.jsonl")
        if self.enabled:
            self.write(
                "request_start",
                question=question,
                mode=mode,
                backend=backend,
                model=_model_for_backend(backend),
                repo=config.current_repo().name,
                target_code_path=config.current_target_code_path(),
            )

    def write(self, event: str, **fields: Any) -> None:
        if not self.enabled:
            return
        try:
            os.makedirs(config.LLM_TRACE_DIR, exist_ok=True)
            row = {
                "ts": _now(),
                "request_id": self.request_id,
                "event": event,
                **fields,
            }
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(_jsonable(row), ensure_ascii=False) + "\n")
        except Exception:
            pass


def _model_for_backend(backend: str) -> str:
    if backend == "cache":
        return ""
    if backend == "sdk":
        return config.SDK_MODEL
    return config.LLM_MODEL


def _jsonable(value: Any) -> Any:
    """Convert provider SDK objects into JSON-serializable data."""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if hasattr(value, "model_dump"):
        try:
            return _jsonable(value.model_dump())
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        try:
            return _jsonable(vars(value))
        except Exception:
            pass
    return repr(value)
