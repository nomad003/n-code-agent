"""Read-only helpers for the LLM trace viewer."""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from . import config


def list_traces(*, limit: int | None = None) -> list[dict[str, Any]]:
    """Return recent trace files, newest first."""
    trace_dir = config.LLM_TRACE_DIR
    if not os.path.isdir(trace_dir):
        return []
    max_files = config.LLM_TRACE_VIEW_MAX_FILES if limit is None else limit
    files: list[tuple[float, str]] = []
    for name in os.listdir(trace_dir):
        if not name.endswith(".jsonl"):
            continue
        path = os.path.join(trace_dir, name)
        if os.path.isfile(path):
            try:
                files.append((os.path.getmtime(path), name))
            except OSError:
                continue
    out: list[dict[str, Any]] = []
    for mtime, name in sorted(files, reverse=True)[:max_files]:
        path = os.path.join(trace_dir, name)
        first = _first_row(path)
        last = _last_row(path)
        try:
            size = os.path.getsize(path)
        except OSError:
            size = 0
        out.append(
            {
                "file": name,
                "mtime": datetime.fromtimestamp(mtime).isoformat(timespec="seconds"),
                "size": size,
                "question": first.get("question", ""),
                "mode": first.get("mode", ""),
                "backend": first.get("backend", ""),
                "model": first.get("model", ""),
                "last_event": last.get("event", ""),
                "last_ts": last.get("ts", ""),
            }
        )
    return out


def read_trace(name: str) -> dict[str, Any]:
    """Read one trace file by basename. Raises ValueError/FileNotFoundError."""
    path = _resolve_trace_file(name)
    rows: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                rows.append({"event": "parse_error", "error": str(exc), "raw": line})
    first = rows[0] if rows else {}
    return {
        "file": os.path.basename(path),
        "question": first.get("question", ""),
        "mode": first.get("mode", ""),
        "backend": first.get("backend", ""),
        "model": first.get("model", ""),
        "rows": rows,
    }


def _resolve_trace_file(name: str) -> str:
    base = os.path.basename(name or "")
    if base != name or not base.endswith(".jsonl"):
        raise ValueError("invalid trace file name")
    root = os.path.abspath(config.LLM_TRACE_DIR)
    path = os.path.abspath(os.path.join(root, base))
    if path != root and not path.startswith(root + os.sep):
        raise ValueError("invalid trace file path")
    if not os.path.isfile(path):
        raise FileNotFoundError(base)
    return path


def _first_row(path: str) -> dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    return json.loads(line)
    except (OSError, json.JSONDecodeError):
        return {}
    return {}


def _last_row(path: str) -> dict[str, Any]:
    last: dict[str, Any] = {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    try:
                        last = json.loads(line)
                    except json.JSONDecodeError:
                        last = {"event": "parse_error"}
    except OSError:
        return {}
    return last
