"""Code-search tools exposed to the LLM agent.

Each tool operates strictly inside ``config.TARGET_CODE_PATH``. Paths coming
from the model are sandboxed: they are resolved relative to the target root and
rejected if they escape it. Tool results are size-capped so a single call can't
blow the model's context window.

This module is intentionally the only place that touches the filesystem, so the
planned offline index (方案 2) can replace these implementations behind the same
schemas without changing ``agent.py``.
"""
import os
import re

import config

# --- Path sandboxing -------------------------------------------------------


class ToolError(Exception):
    """Raised for a bad tool argument; the message is fed back to the model."""


def _resolve(rel_path: str) -> str:
    """Resolve a model-supplied path against the target root, safely.

    Returns an absolute path guaranteed to live inside TARGET_CODE_PATH.
    """
    rel_path = (rel_path or "").strip()
    # Treat "", ".", "/" and absolute-looking inputs as the repo root.
    rel_path = rel_path.lstrip("/")
    root = config.TARGET_CODE_PATH
    abs_path = os.path.normpath(os.path.join(root, rel_path))
    # Ensure the resolved path is the root itself or a descendant of it.
    if abs_path != root and not abs_path.startswith(root + os.sep):
        raise ToolError(f"path escapes the target codebase: {rel_path!r}")
    return abs_path


def _rel(abs_path: str) -> str:
    """Path relative to the target root, for display back to the model."""
    rel = os.path.relpath(abs_path, config.TARGET_CODE_PATH)
    return "." if rel == "." else rel


# --- Tool implementations --------------------------------------------------


_REGEX_META = set(r".^$*+?{}[]\|()")


def _is_plain_text(pattern: str) -> bool:
    """True if the pattern has no regex metacharacters (a literal search)."""
    return not any(ch in _REGEX_META for ch in pattern)


def grep_code(pattern: str, path: str = ".") -> str:
    """Search files under ``path`` for ``pattern`` (a regular expression)."""
    if not pattern:
        raise ToolError("pattern is required")
    base = _resolve(path)
    if not os.path.exists(base):
        raise ToolError(f"path does not exist: {path!r}")

    # Fast path: whole-repo literal search via the FTS index. Only when the
    # pattern is plain text (FTS can't do regex) and the scope is the whole repo
    # (the index isn't path-scoped). Otherwise fall through to the live scan.
    if path in (".", "", "/") and _is_plain_text(pattern):
        try:
            import index_query

            hits = index_query.search_fts(pattern, limit=config.MAX_GREP_MATCHES)
        except Exception:
            hits = None
        if hits is not None:
            if not hits:
                return f"no matches for {pattern!r} under {_rel(base)}"
            lines = [f"{h['path']}:{h['line']}: {h['text']}" for h in hits]
            if len(hits) >= config.MAX_GREP_MATCHES:
                lines.append(f"... (truncated at {config.MAX_GREP_MATCHES} matches)")
            return "\n".join(lines)

    try:
        regex = re.compile(pattern)
    except re.error as exc:
        raise ToolError(f"invalid regex {pattern!r}: {exc}")

    matches: list[str] = []
    for file_path in _iter_files(base):
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
                for lineno, line in enumerate(fh, start=1):
                    if regex.search(line):
                        matches.append(
                            f"{_rel(file_path)}:{lineno}: {line.rstrip()[:300]}"
                        )
                        if len(matches) >= config.MAX_GREP_MATCHES:
                            matches.append(
                                f"... (truncated at {config.MAX_GREP_MATCHES} matches)"
                            )
                            return "\n".join(matches)
        except (OSError, UnicodeError):
            continue

    if not matches:
        return f"no matches for {pattern!r} under {_rel(base)}"
    return "\n".join(matches)


def read_file(path: str, start: int = 1, end: int | None = None) -> str:
    """Read lines [start, end] (1-based, inclusive) of a file."""
    abs_path = _resolve(path)
    if not os.path.isfile(abs_path):
        raise ToolError(f"not a file: {path!r}")

    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError as exc:
        raise ToolError(f"cannot read {path!r}: {exc}")

    total = len(lines)
    start = max(1, int(start))
    end = total if end is None else min(total, int(end))
    if start > total:
        return f"{_rel(abs_path)} has {total} lines; start={start} is past EOF"

    selected = lines[start - 1 : end]
    body = "".join(selected)
    if len(body) > config.MAX_READ_BYTES:
        body = body[: config.MAX_READ_BYTES] + "\n... (truncated)"

    numbered = []
    for offset, line in enumerate(body.splitlines(), start=start):
        numbered.append(f"{offset}\t{line}")
    header = f"# {_rel(abs_path)} (lines {start}-{end} of {total})"
    return header + "\n" + "\n".join(numbered)


def list_dir(path: str = ".") -> str:
    """List the entries of a directory (one level), dirs marked with a trailing /."""
    abs_path = _resolve(path)
    if not os.path.isdir(abs_path):
        raise ToolError(f"not a directory: {path!r}")

    entries: list[str] = []
    try:
        names = sorted(os.listdir(abs_path))
    except OSError as exc:
        raise ToolError(f"cannot list {path!r}: {exc}")

    for name in names:
        if name.startswith(".") or name == "__pycache__":
            continue
        full = os.path.join(abs_path, name)
        entries.append(name + "/" if os.path.isdir(full) else name)
        if len(entries) >= config.MAX_LIST_ENTRIES:
            entries.append(f"... (truncated at {config.MAX_LIST_ENTRIES} entries)")
            break

    if not entries:
        return f"{_rel(abs_path)} is empty"
    return f"# {_rel(abs_path)}/\n" + "\n".join(entries)


def find_symbol(name: str) -> str:
    """Locate likely definitions of a class/function/variable named ``name``.

    Uses the offline index when available (exact, fast); falls back to a
    regex scan over the tree otherwise.
    """
    if not name:
        raise ToolError("name is required")

    # Fast path: offline symbol index.
    try:
        import index_query

        rows = index_query.find_symbol(name)
    except Exception:
        rows = None
    if rows:
        lines = [f"{r['path']}:{r['line']}: [{r['kind']}] {r['name']}" for r in rows]
        return "\n".join(lines)
    # rows == [] means the index exists but has no match; rows is None means no
    # index. Either way, fall through to the live scan for best-effort leads.

    ident = re.escape(name)
    # Common definition forms across Python / C-like / Lua game code
    # (server, combat, client, engine).
    pattern = (
        rf"(class\s+{ident}\b"
        rf"|def\s+{ident}\b"
        rf"|function\s+{ident}\b"
        rf"|{ident}\s*[:=]\s*function"
        rf"|(?:struct|interface|enum|type)\s+{ident}\b"
        rf"|func\s+(?:\([^)]*\)\s+)?{ident}\b)"
    )
    result = grep_code(pattern, ".")
    if result.startswith("no matches"):
        # Fall back to a plain symbol search so the model still gets leads.
        return grep_code(rf"\b{ident}\b", ".")
    return result


# --- Filesystem traversal helper ------------------------------------------

_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".idea"}
_BINARY_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".gz", ".tar",
    ".so", ".dll", ".exe", ".bin", ".o", ".a", ".pyc", ".jar", ".class",
    ".mp3", ".wav", ".mp4", ".ttf", ".woff", ".woff2",
}


def _iter_files(base: str):
    """Yield text-ish file paths under ``base`` (or ``base`` itself if a file)."""
    if os.path.isfile(base):
        yield base
        return
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS and not d.startswith(".")]
        for fname in files:
            if os.path.splitext(fname)[1].lower() in _BINARY_EXT:
                continue
            yield os.path.join(root, fname)


# --- Schemas + dispatch ----------------------------------------------------

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "grep_code",
            "description": "在目标代码库中按正则搜索符号或关键字，返回 文件:行号: 内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "正则表达式"},
                    "path": {
                        "type": "string",
                        "description": "搜索范围（相对路径，默认整个代码库 '.'）",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取某文件的指定行范围（1-based，含端点）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件相对路径"},
                    "start": {"type": "integer", "description": "起始行，默认 1"},
                    "end": {"type": "integer", "description": "结束行，默认到文件末尾"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "列出某个目录下的条目（单层），目录以 / 结尾。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "目录相对路径，默认根目录 '.'",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_symbol",
            "description": "查找某个类/函数/类型的定义位置。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "符号名称"}
                },
                "required": ["name"],
            },
        },
    },
]

# Maps tool name -> implementation. The agent loop calls through this registry.
TOOL_REGISTRY = {
    "grep_code": grep_code,
    "read_file": read_file,
    "list_dir": list_dir,
    "find_symbol": find_symbol,
}


def dispatch(name: str, arguments: dict) -> str:
    """Run a tool by name with keyword arguments; return a string result.

    Tool/argument errors are returned as strings (not raised) so the agent loop
    can feed them back to the model as a tool result and let it recover.
    """
    fn = TOOL_REGISTRY.get(name)
    if fn is None:
        return f"error: unknown tool {name!r}"
    try:
        return fn(**(arguments or {}))
    except ToolError as exc:
        return f"error: {exc}"
    except TypeError as exc:
        return f"error: bad arguments for {name}: {exc}"
    except Exception as exc:  # defensive: never crash the loop on a tool
        return f"error: {name} failed: {exc}"
