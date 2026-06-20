"""Code-search tools exposed to the LLM agent.

Each tool operates strictly inside the current configured target repo. Paths coming
from the model are sandboxed: they are resolved relative to the target root and
rejected if they escape it. Tool results are size-capped so a single call can't
blow the model's context window.

This module is intentionally the only place that touches the filesystem, so the
planned offline index (方案 2) can replace these implementations behind the same
schemas without changing ``code_agent.core.agent``.
"""
import os
import re

from .. import config

# --- Path sandboxing -------------------------------------------------------


class ToolError(Exception):
    """Raised for a bad tool argument; the message is fed back to the model."""


def _resolve(rel_path: str) -> str:
    """Resolve a model-supplied path against the target root, safely.

    Returns an absolute path guaranteed to live inside the current repo root.
    """
    rel_path = (rel_path or "").strip()
    # Treat "", ".", "/" and absolute-looking inputs as the repo root.
    rel_path = rel_path.lstrip("/")
    root = config.current_target_code_path()
    abs_path = os.path.normpath(os.path.join(root, rel_path))
    # Ensure the resolved path is the root itself or a descendant of it.
    if abs_path != root and not abs_path.startswith(root + os.sep):
        raise ToolError(f"path escapes the target codebase: {rel_path!r}")
    return abs_path


def _rel(abs_path: str) -> str:
    """Path relative to the target root, for display back to the model."""
    rel = os.path.relpath(abs_path, config.current_target_code_path())
    return "." if rel == "." else rel


# --- Tool implementations --------------------------------------------------


_REGEX_META = set(r".^$*+?{}[]\|()")


def _is_plain_text(pattern: str) -> bool:
    """True if the pattern has no regex metacharacters (a literal search)."""
    return not any(ch in _REGEX_META for ch in pattern)


_GREP_OUTPUT_MODES = ("content", "files", "count")


def grep_code(
    pattern: str,
    path: str = ".",
    context: int = 0,
    output_mode: str = "content",
    head_limit: int = 0,
) -> str:
    """Search files under ``path`` for ``pattern`` (a regular expression).

    ``output_mode``:
    - ``"content"`` (default): ``path:NN: line`` per match; ``context`` (0..5)
      adds N lines around each hit in grep -C style. Best for understanding a
      few specific call sites.
    - ``"files"``: distinct file paths only, one per line (alphabetical). Best
      for enumeration ("which modules touch X?") — cheapest by far.
    - ``"count"``: ``path: N`` per file, sorted by descending hit count.

    ``head_limit`` (>0) caps how many lines / files the result returns, on top
    of the server-side ``MAX_GREP_MATCHES`` cap on raw matches scanned.
    """
    if not pattern:
        raise ToolError("pattern is required")
    base = _resolve(path)
    if not os.path.exists(base):
        raise ToolError(f"path does not exist: {path!r}")
    context = max(0, min(5, int(context)))
    head_limit = max(0, int(head_limit))
    if output_mode not in _GREP_OUTPUT_MODES:
        raise ToolError(
            f"invalid output_mode {output_mode!r}; expected one of {_GREP_OUTPUT_MODES}"
        )

    # Enumeration modes collapse to one entry per file, so a much larger raw
    # scan budget is safe. Content mode keeps the tight per-match cap.
    raw_cap = config.MAX_GREP_FILES if output_mode in ("files", "count") else config.MAX_GREP_MATCHES

    # Fast path: whole-repo literal search via the FTS index. Only when the
    # pattern is plain text (FTS can't do regex) and the scope is the whole repo
    # (the index isn't path-scoped). Otherwise fall through to the live scan.
    if path in (".", "", "/") and _is_plain_text(pattern):
        try:
            from . import index_query

            hits = index_query.search_fts(pattern, limit=raw_cap)
        except Exception:
            hits = None
        if hits is not None:
            if not hits:
                return f"no matches for {pattern!r} under {_rel(base)}"
            matches = [
                {"path": h["path"], "line": h["line"], "text": h["text"]} for h in hits
            ]
            truncated = len(hits) >= raw_cap
            return _format_grep(matches, context, truncated, output_mode, head_limit, raw_cap)

    try:
        regex = re.compile(pattern)
    except re.error as exc:
        raise ToolError(f"invalid regex {pattern!r}: {exc}")

    # Fast path: ripgrep is 10-100x faster than a Python re scan on large repos
    # and shares the same output shape ("path:line:text"), so we can hand its
    # output straight to `_format_grep`. Falls back to the pure-Python scan if
    # rg is unavailable or fails for any reason.
    rg_matches = _grep_with_ripgrep(pattern, base, raw_cap)
    if rg_matches is not None:
        matches, truncated = rg_matches
        if not matches:
            return f"no matches for {pattern!r} under {_rel(base)}"
        return _format_grep(matches, context, truncated, output_mode, head_limit, raw_cap)

    matches: list[dict] = []
    truncated = False
    for file_path in _iter_files(base):
        if truncated:
            break
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
                for lineno, line in enumerate(fh, start=1):
                    if regex.search(line):
                        matches.append(
                            {
                                "path": _rel(file_path),
                                "line": lineno,
                                "text": line.rstrip()[:300],
                            }
                        )
                        if len(matches) >= raw_cap:
                            truncated = True
                            break
        except (OSError, UnicodeError):
            continue

    if not matches:
        return f"no matches for {pattern!r} under {_rel(base)}"
    return _format_grep(matches, context, truncated, output_mode, head_limit, raw_cap)


def _format_grep(
    matches: list[dict],
    context: int,
    truncated: bool,
    output_mode: str = "content",
    head_limit: int = 0,
    raw_cap: int = 0,
) -> str:
    """Render grep matches in the requested ``output_mode``."""
    if output_mode == "files":
        seen: list[str] = []
        seen_set: set[str] = set()
        for m in matches:
            p = m["path"]
            if p not in seen_set:
                seen_set.add(p)
                seen.append(p)
        seen.sort()
        if head_limit and len(seen) > head_limit:
            extra = len(seen) - head_limit
            seen = seen[:head_limit]
            seen.append(f"... (+{extra} more files; raise head_limit to see all)")
        elif truncated:
            seen.append(f"... (raw match scan truncated at {raw_cap or config.MAX_GREP_MATCHES})")
        return "\n".join(seen)

    if output_mode == "count":
        counts: dict[str, int] = {}
        for m in matches:
            counts[m["path"]] = counts.get(m["path"], 0) + 1
        ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        if head_limit and len(ranked) > head_limit:
            extra = len(ranked) - head_limit
            ranked = ranked[:head_limit]
            tail = f"\n... (+{extra} more files; raise head_limit to see all)"
        elif truncated:
            tail = f"\n... (raw match scan truncated at {raw_cap or config.MAX_GREP_MATCHES})"
        else:
            tail = ""
        return "\n".join(f"{p}: {n}" for p, n in ranked) + tail

    # content mode (default)
    if context <= 0:
        lines = [f"{m['path']}:{m['line']}: {m['text']}" for m in matches]
        if head_limit and len(lines) > head_limit:
            extra = len(lines) - head_limit
            lines = lines[:head_limit]
            lines.append(f"... (+{extra} more matches; raise head_limit to see all)")
        elif truncated:
            lines.append(f"... (truncated at {raw_cap or config.MAX_GREP_MATCHES} matches)")
        return "\n".join(lines)

    # Group by file, merge overlapping windows around each match.
    by_file: dict[str, list[dict]] = {}
    for m in matches:
        by_file.setdefault(m["path"], []).append(m)

    out_blocks: list[str] = []
    for rel_path, file_hits in by_file.items():
        abs_path = _resolve(rel_path)
        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
                file_lines = fh.readlines()
        except OSError:
            # Fall back to flat output for files we can't re-read.
            for m in file_hits:
                out_blocks.append(f"{m['path']}:{m['line']}: {m['text']}")
            continue

        match_nos = sorted({h["line"] for h in file_hits})
        # Merge [line-context, line+context] windows into hunks.
        hunks: list[tuple[int, int]] = []
        for lineno in match_nos:
            lo = max(1, lineno - context)
            hi = min(len(file_lines), lineno + context)
            if hunks and lo <= hunks[-1][1] + 1:
                hunks[-1] = (hunks[-1][0], max(hunks[-1][1], hi))
            else:
                hunks.append((lo, hi))

        match_set = set(match_nos)
        for lo, hi in hunks:
            block: list[str] = []
            for ln in range(lo, hi + 1):
                marker = ":" if ln in match_set else "-"
                text = file_lines[ln - 1].rstrip()[:300]
                block.append(f"{rel_path}:{ln}{marker} {text}")
            out_blocks.append("\n".join(block))

    if head_limit and len(out_blocks) > head_limit:
        extra = len(out_blocks) - head_limit
        out_blocks = out_blocks[:head_limit]
        tail = f"\n--\n... (+{extra} more hunks; raise head_limit to see all)"
    elif truncated:
        tail = f"\n... (truncated at {raw_cap or config.MAX_GREP_MATCHES} matches)"
    else:
        tail = ""
    return "\n--\n".join(out_blocks) + tail


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


def glob(pattern: str, path: str = ".", head_limit: int = 0) -> str:
    """List files whose relative path matches a fnmatch/glob pattern.

    Supports ``*`` (within a path segment), ``**`` (any depth), ``?``, and
    bracket classes. Results are sorted by mtime descending so recently-touched
    code surfaces first (mirrors Claude Code's Glob tool behaviour). Cheaper
    than grep_code when you only need to enumerate files by name.
    """
    import fnmatch

    if not pattern:
        raise ToolError("pattern is required")
    base = _resolve(path)
    if not os.path.isdir(base):
        raise ToolError(f"not a directory: {path!r}")
    head_limit = max(0, int(head_limit))

    # Translate ** segments so fnmatch's per-segment matching becomes recursive.
    # fnmatch.translate handles single '*' fine; we just normalize '**/x' into
    # '*x' / 'x' alternatives by matching against every path depth.
    has_recursive = "**" in pattern

    def candidate_paths():
        # Always anchor on `base`. We want repo-relative posix paths so the
        # model can match exactly what it sees in grep_code output.
        for fp in _iter_files(base):
            rel = os.path.relpath(fp, base).replace(os.sep, "/")
            yield fp, rel

    if has_recursive:
        # Two cheap tricks:
        # 1) '**/foo' -> match any depth: also try fnmatch against the basename.
        # 2) 'a/**/b' -> split on '**' and require both halves to bound the path.
        head, _, tail = pattern.partition("**")
        head = head.rstrip("/")
        tail = tail.lstrip("/")

        def matches(rel: str) -> bool:
            if head and not (rel.startswith(head + "/") or rel == head):
                return False
            if not tail:
                return True
            # Tail must match against any suffix of the remaining path.
            remainder = rel[len(head) + 1 :] if head else rel
            parts = remainder.split("/")
            for i in range(len(parts)):
                suffix = "/".join(parts[i:])
                if fnmatch.fnmatchcase(suffix, tail):
                    return True
                # Allow '**/foo.cpp' to match basename even if foo.cpp is in root.
                if "/" not in tail and fnmatch.fnmatchcase(parts[-1], tail):
                    return True
            return False
    else:
        def matches(rel: str) -> bool:
            return fnmatch.fnmatchcase(rel, pattern) or (
                "/" not in pattern and fnmatch.fnmatchcase(rel.rsplit("/", 1)[-1], pattern)
            )

    hits: list[tuple[float, str]] = []
    for fp, rel in candidate_paths():
        if matches(rel):
            try:
                mtime = os.path.getmtime(fp)
            except OSError:
                mtime = 0.0
            hits.append((mtime, _rel(fp)))

    if not hits:
        return f"no files matching {pattern!r} under {_rel(base)}"
    hits.sort(key=lambda t: (-t[0], t[1]))
    paths = [p for _, p in hits]

    if head_limit and len(paths) > head_limit:
        extra = len(paths) - head_limit
        paths = paths[:head_limit]
        paths.append(f"... (+{extra} more files; raise head_limit to see all)")
    elif len(paths) >= config.MAX_LIST_ENTRIES:
        paths.append(f"... (truncated at {config.MAX_LIST_ENTRIES})")
    return "\n".join(paths)


def find_symbol(name: str) -> str:
    """Locate likely definitions of a class/function/variable named ``name``.

    Uses the offline index when available (exact, fast); falls back to a
    regex scan over the tree otherwise.
    """
    if not name:
        raise ToolError("name is required")

    # Fast path: offline symbol index.
    try:
        from . import index_query

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


def resolve_frame(frame: str) -> str:
    """Map a backtrace frame's function to its definition(s).

    Accepts a full frame signature like ``SceneMgr::Update(int, float)`` and
    uses the class name (if any) to narrow same-name candidates. Falls back to
    a plain ``find_symbol`` on the bare name.
    """
    if not frame:
        raise ToolError("frame is required")
    try:
        from ..diagnostics import diagnose

        frames = diagnose.resolve_frames([
            diagnose.Frame(num=0, func_raw=frame, func=frame)
        ])
    except Exception:
        frames = []
    if frames and frames[0].candidates:
        cands = frames[0].candidates
        lines = [f"{c['path']}:{c['line']}: [{c['kind']}] {c['name']}" for c in cands]
        return "\n".join(lines)
    # No index hit: fall back to the bare-name symbol search.
    bare = frame.split("(")[0].split("::")[-1].strip()
    return find_symbol(bare) if bare else f"no resolution for {frame!r}"


def find_log_source(message: str) -> str:
    """Locate the code that prints a given runtime log line.

    The log line is a format string with its values filled in; this strips the
    timestamp/level prefix and runtime values, then full-text-searches the
    fixed text against the codebase.
    """
    if not message:
        raise ToolError("message is required")
    try:
        from ..diagnostics import diagnose

        hits = diagnose.find_log_source(message)
    except Exception:
        hits = []
    if hits:
        return "\n".join(f"{h['path']}:{h['line']}: {h['text']}" for h in hits)
    # Fall back to a literal grep of the longest fixed fragment, if any.
    try:
        from ..diagnostics import diagnose

        runs = diagnose._literal_runs(message)
    except Exception:
        runs = []
    if runs:
        return grep_code(runs[0], ".")
    return f"no log source found for {message!r}"


def find_assert_context(message: str, context: int = 8) -> str:
    """Locate assert/check sites related to an error log and include context."""
    if not message:
        raise ToolError("message is required")
    context = max(2, min(30, int(context)))
    hits = None
    try:
        from . import index_query

        hits = index_query.search_asserts(message, limit=10)
    except Exception:
        hits = None
    if hits is None:
        return (
            "assert index is unavailable; build/update it with "
            "`python -m code_agent.retrieval.indexer --repo <name>`"
        )
    if not hits:
        # Fall back to existing log-source lookup so the agent still gets leads.
        log_hit = find_log_source(message)
        if not log_hit.startswith("no log source found"):
            return "no indexed assert matched; related log source candidates:\n" + log_hit
        return f"no indexed assert matched {message!r}"

    try:
        from ..kb import assert_knowledge

        playbook = assert_knowledge.format_for_hits(hits, query=message)
    except Exception:
        playbook = ""
    blocks: list[str] = []
    if playbook:
        blocks.append(playbook)
    for h in hits:
        line = int(h["line"])
        start = max(1, line - context)
        end = line + context
        snippet = read_file(h["path"], start=start, end=end)
        msg = f" message={h['message']!r}" if h.get("message") else ""
        match = h.get("match") or "text"
        reason = (
            "fixed-text match"
            if match == "text"
            else "near file:line hint; line may be inaccurate"
        )
        blocks.append(
            f"{h['path']}:{line}: [{h['macro']}] ({reason}){msg}\n"
            f"assert: {h['statement']}\n"
            "note: treat this as a candidate; confirm with surrounding code and build version.\n"
            f"context:\n{snippet}"
        )
    return "\n\n---\n\n".join(blocks)


def recall_knowledge(query: str) -> str:
    """Recall related knowledge precipitated from past Q&A (方案 3).

    Returns historical conclusions as *leads* — they may be stale (the code may
    have changed since), so verify with read_file before relying on them. Empty
    when the flywheel is off or nothing matches.
    """
    if not query:
        raise ToolError("query is required")
    try:
        from ..kb import knowledge

        hits = knowledge.recall(query)
    except Exception:
        hits = []
    if not hits:
        return "no related knowledge found"
    out = []
    for h in hits:
        tag = " [⚠️已过时，需重新核实]" if h["stale"] else ""
        refs = (" 涉及: " + ", ".join(h["refs"])) if h["refs"] else ""
        out.append(f"Q: {h['question']}{tag}{refs}\nA: {h['answer'][:500]}")
    return "\n\n".join(out)


def repo_overview() -> str:
    """Return the cached repository navigation/profile for the current repo."""
    try:
        from . import repo_profile

        profile = repo_profile.load()
        if not profile:
            return (
                "no repository profile found; build it with "
                "`python -m code_agent.retrieval.repo_profile --repo <name>`"
            )
        return repo_profile.format_for_prompt(profile)
    except Exception as exc:
        return f"error: repo_overview failed: {exc}"


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
    for root, dirs, files in os.walk(base, followlinks=True):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS and not d.startswith(".")]
        for fname in files:
            if os.path.splitext(fname)[1].lower() in _BINARY_EXT:
                continue
            yield os.path.join(root, fname)


# Cache the ripgrep binary location: shutil.which is cheap but we hit grep_code
# many times per request. None = explicitly probed and not found.
_RG_PATH: "str | None | type[NotImplementedError]" = NotImplementedError


def _ripgrep_path() -> "str | None":
    global _RG_PATH
    if _RG_PATH is NotImplementedError:
        import shutil

        _RG_PATH = shutil.which("rg")
    return _RG_PATH  # type: ignore[return-value]


def _grep_with_ripgrep(pattern: str, base: str, cap: int):
    """Run ripgrep under ``base`` for ``pattern``; return ``(matches, truncated)``
    or ``None`` if rg is unavailable / errored / not applicable.

    Output is normalized to the same list-of-dicts shape as the Python scan so
    ``_format_grep`` doesn't care which backend produced it. ``cap`` bounds the
    raw match count; the caller picks it based on output_mode.
    """
    rg = _ripgrep_path()
    if not rg:
        return None
    if not os.path.isdir(base):
        # rg works on files too, but our Python fallback already handles that
        # corner case; let it own single-file scans (rare in practice).
        return None
    import subprocess

    # -uu: don't honor .gitignore / hidden (parity with the Python iterator).
    # --no-heading: machine-readable "path:line:text" per match.
    # --color never: no ANSI escapes in stdout.
    # -e <pat> -- <path>: avoid arg injection if pattern starts with '-'.
    args = [
        rg,
        "--line-number",
        "--no-heading",
        "--color", "never",
        "--follow",
        "-uu",
        "-e", pattern,
        "--",
        base,
    ]
    try:
        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, ValueError):
        return None

    matches: list[dict] = []
    truncated = False
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            # Expected: "<abs_path>:<lineno>:<text>". Skip anything malformed
            # (rg sometimes emits a final empty line on truncation).
            parts = line.rstrip("\n").split(":", 2)
            if len(parts) < 3:
                continue
            abs_path, lineno_s, text = parts
            try:
                lineno = int(lineno_s)
            except ValueError:
                continue
            try:
                rel = _rel(abs_path)
            except Exception:
                rel = abs_path
            matches.append({"path": rel, "line": lineno, "text": text[:300]})
            if len(matches) >= cap:
                truncated = True
                break
    finally:
        # Drain or kill — letting Popen go out of scope mid-stream causes a
        # ResourceWarning and on truncated input rg keeps running.
        try:
            if proc.poll() is None:
                proc.kill()
            proc.stdout.close()  # type: ignore[union-attr]
            proc.wait(timeout=2)
        except Exception:
            pass

    # Exit code 1 = no matches (not an error); 2+ = real problem → fall back.
    rc = proc.returncode
    if rc not in (0, 1, None, -9):  # -9 = SIGKILL from our truncation
        return None
    return matches, truncated


# --- Schemas + dispatch ----------------------------------------------------

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "grep_code",
            "description": (
                "在目标代码库中按正则搜索。**枚举型问题（'哪些模块/文件用到 X'）**优先用 "
                "output_mode='files' 或 'count'，只回路径列表，token 成本最低；"
                "需要看代码细节时用 output_mode='content' + context=3（一次拿到上下文，"
                "通常无需再调 read_file）。head_limit 可截断结果。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "正则表达式"},
                    "path": {
                        "type": "string",
                        "description": "搜索范围（相对路径，默认整个代码库 '.'）",
                    },
                    "output_mode": {
                        "type": "string",
                        "enum": ["content", "files", "count"],
                        "description": (
                            "content=每条命中 'path:行号: 文本'（默认，可配合 context）；"
                            "files=只回去重后的文件路径列表；"
                            "count=按文件出现次数排序（'path: N'）。"
                        ),
                    },
                    "context": {
                        "type": "integer",
                        "description": "content 模式下每个命中前后展示的行数（0..5，默认 0）。优先用它替代 read_file 取上下文。",
                    },
                    "head_limit": {
                        "type": "integer",
                        "description": "返回结果上限（0=不限）：files/count 限文件数，content 限命中或 hunk 数。",
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
            "name": "glob",
            "description": (
                "按 fnmatch/glob 模式（支持 *、**、?）列出匹配的文件路径，按 mtime 倒序。"
                "**当你只关心'有哪些文件'而不关心内容**（例如 '所有 *MonsterAI*.cpp'、"
                "'lua/quest 下的脚本'）时，优先用 glob 而不是 grep_code 全文搜索——更便宜。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "fnmatch 风格的路径模式，如 '**/Monster*.cpp'、'lua/quest/*.lua'",
                    },
                    "path": {
                        "type": "string",
                        "description": "起始目录（默认整个代码库 '.'）",
                    },
                    "head_limit": {
                        "type": "integer",
                        "description": "返回文件数上限（0=不限）",
                    },
                },
                "required": ["pattern"],
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
    {
        "type": "function",
        "function": {
            "name": "repo_overview",
            "description": "查看已缓存的代码库导航/项目概览/常用模块候选，适合在宽泛问题开始时作为检索起点。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "resolve_frame",
            "description": "把崩溃栈某一帧的函数（如 'SceneMgr::Update(int)'）定位到代码定义；带类名时会自动收窄同名候选。",
            "parameters": {
                "type": "object",
                "properties": {
                    "frame": {
                        "type": "string",
                        "description": "栈帧的函数签名，可含类名/命名空间/参数",
                    }
                },
                "required": ["frame"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_log_source",
            "description": "根据一条运行时日志（含具体变量值）反查打印它的代码位置；会自动剥掉时间戳并把变量归一化为格式串再检索。",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "运行时看到的日志行（可含时间戳/级别前缀和变量值）",
                    }
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_assert_context",
            "description": (
                "根据断言失败、ASSERT/CHECK 报错或相关错误日志，查询离线 assert 索引，"
                "返回最相关的断言语句、文件行号和附近代码上下文。用户贴 assert 日志时优先用它。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "运行时看到的断言/错误日志，可含时间戳、变量值、文件行号",
                    },
                    "context": {
                        "type": "integer",
                        "description": "返回断言行前后的上下文行数，默认 8，范围 2..30",
                    },
                },
                "required": ["message"],
            },
        },
    },
]

# recall_knowledge is advertised only when the flywheel is enabled (方案 3), so
# the model doesn't see a tool that always returns "nothing".
_RECALL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "recall_knowledge",
        "description": "检索历史问答沉淀的相关结论作为线索（可能已过时，需用 read_file 二次核实）。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "要检索的问题/关键词"}
            },
            "required": ["query"],
        },
    },
}


def active_schemas() -> list[dict]:
    """Tool schemas to advertise, adjusted for runtime config (方案 3)."""
    if config.USE_KNOWLEDGE:
        return TOOL_SCHEMAS + [_RECALL_SCHEMA]
    return TOOL_SCHEMAS


# Maps tool name -> implementation. The agent loop calls through this registry.
TOOL_REGISTRY = {
    "grep_code": grep_code,
    "read_file": read_file,
    "list_dir": list_dir,
    "glob": glob,
    "find_symbol": find_symbol,
    "repo_overview": repo_overview,
    "resolve_frame": resolve_frame,
    "find_log_source": find_log_source,
    "find_assert_context": find_assert_context,
    "recall_knowledge": recall_knowledge,
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
