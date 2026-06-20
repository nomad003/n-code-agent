"""Read-only queries against the offline index (方案 2).

Used by tools.find_symbol / tools.grep_code when an index exists. All functions
are defensive: if the DB is missing/unusable they return None so the caller can
fall back to live filesystem scanning. The index is opened read-only per call
(cheap for SQLite; keeps the module stateless and fork/thread-safe).
"""
from __future__ import annotations

import os
import re
import sqlite3

from .. import config


def available() -> bool:
    """True if an index DB exists and the index is enabled."""
    return config.USE_INDEX and os.path.isfile(config.current_index_db_path())


def _connect() -> sqlite3.Connection | None:
    if not available():
        return None
    try:
        # immutable=1: open read-only, assume the file won't change under us.
        uri = f"file:{config.current_index_db_path()}?mode=ro"
        return sqlite3.connect(uri, uri=True)
    except sqlite3.Error:
        return None


def find_symbol(name: str, *, limit: int = 50) -> list[dict] | None:
    """Exact-name symbol lookup. Returns rows or None if no index."""
    conn = _connect()
    if conn is None:
        return None
    try:
        rows = conn.execute(
            "SELECT name, kind, path, line FROM symbols WHERE name = ? "
            "ORDER BY (kind='method'), path, line LIMIT ?",
            (name, limit),
        ).fetchall()
    except sqlite3.Error:
        return None
    finally:
        conn.close()
    return [
        {"name": r[0], "kind": r[1], "path": r[2], "line": r[3]} for r in rows
    ]


def search_fts(query: str, *, limit: int = 100) -> list[dict] | None:
    """Full-text search over file contents (FTS5). Returns matching lines.

    FTS5 finds matching *files*; we then locate the matching lines within each
    file's stored content so the result mirrors grep (path:line: text).
    """
    conn = _connect()
    if conn is None:
        return None
    fts_query = _fts_prefilter(query)
    if fts_query is None:
        # No usable tokens (e.g. punctuation-only) → can't prefilter via FTS;
        # signal "no index path" so the caller falls back to a live scan.
        conn.close()
        return None
    try:
        # FTS is only a FILE prefilter (AND of the query's tokens): any line
        # literally containing the query implies its file contains all tokens.
        # The authoritative grep match is the per-line substring scan below, so
        # tokens needn't be adjacent (fixes multi-word queries that an adjacent-
        # phrase MATCH would miss).
        file_rows = conn.execute(
            "SELECT path, content FROM files_fts WHERE files_fts MATCH ? LIMIT 1000",
            (fts_query,),
        ).fetchall()
    except sqlite3.Error:
        return None
    finally:
        conn.close()

    out: list[dict] = []
    needle = query.lower()
    for path, content in file_rows:
        for i, line in enumerate(content.splitlines(), start=1):
            if needle in line.lower():
                out.append({"path": path, "line": i, "text": line.rstrip()[:300]})
                if len(out) >= limit:
                    return out
    return out


def search_asserts(query: str, *, limit: int = 20) -> list[dict] | None:
    """Search indexed assert/check sites by runtime log or assert text.

    Returns rows or None if the index is unavailable/too old to have assert
    tables. The caller can fall back to generic log/code search.
    """
    conn = _connect()
    if conn is None:
        return None
    candidates = _assert_queries(query)
    seen: set[tuple[str, int, str]] = set()
    out: list[dict] = []
    locations = _source_locations(query)
    try:
        for fts_query in candidates:
            rows = conn.execute(
                """
                SELECT a.path, a.line, a.macro, a.statement, a.message, a.file_hash
                FROM assert_fts
                JOIN asserts a ON a.id = assert_fts.rowid
                WHERE assert_fts MATCH ?
                ORDER BY a.path, a.line
                LIMIT ?
                """,
                (fts_query, limit),
            ).fetchall()
            for row in rows:
                _append_assert_row(out, seen, row, "text")
        if not out and locations:
            for path_hint, line_hint in locations:
                rows = conn.execute(
                    """
                    SELECT path, line, macro, statement, message, file_hash
                    FROM asserts
                    WHERE (path = ? OR path LIKE ? OR path LIKE ?)
                      AND line BETWEEN ? AND ?
                    ORDER BY ABS(line - ?), path, line
                    LIMIT ?
                    """,
                    (
                        path_hint,
                        f"%/{path_hint}",
                        f"%/{os.path.basename(path_hint)}",
                        max(1, line_hint - 80),
                        line_hint + 80,
                        line_hint,
                        limit,
                    ),
                ).fetchall()
                for row in rows:
                    _append_assert_row(out, seen, row, "near_location")
        if locations:
            out.sort(key=lambda h: _assert_rank(h, locations))
        return out[:limit]
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def _fts_prefilter(query: str) -> str | None:
    """AND-of-tokens FTS query for ``query``; None if it has no usable tokens.

    Tokenizes like unicode61 (alphanumeric runs) so it matches how files_fts
    indexed the content. ANDing tokens keeps the prefilter a correct superset of
    the literal-substring matches the per-line scan then confirms.
    """
    import re

    tokens = re.findall(r"\w+", query, re.UNICODE)
    tokens = [t for t in tokens if t]
    if not tokens:
        return None
    return " AND ".join(f'"{t}"' for t in dict.fromkeys(tokens))


def _assert_queries(query: str) -> list[str]:
    """FTS queries for assert lookup, trying fixed log fragments first."""
    runs: list[str] = []
    try:
        from ..diagnostics import diagnose

        runs.extend(diagnose._literal_runs(query))
    except Exception:
        pass
    runs.append(query)
    out: list[str] = []
    for run in runs:
        fts = _fts_prefilter(run)
        if fts and fts not in out:
            out.append(fts)
    return out


_SOURCE_LOC_RE = re.compile(
    r"(?P<path>[\w./\\-]+\.(?:cpp|cc|cxx|c|h|hpp|hh|hxx))[:(](?P<line>\d+)"
)


def _source_locations(query: str) -> list[tuple[str, int]]:
    """Extract source file/line hints from logs. These are weak hints only."""
    out: list[tuple[str, int]] = []
    for m in _SOURCE_LOC_RE.finditer(query or ""):
        path = m.group("path").replace("\\", "/").lstrip("./")
        try:
            line = int(m.group("line"))
        except ValueError:
            continue
        item = (path, line)
        if item not in out:
            out.append(item)
    return out


def _append_assert_row(
    out: list[dict],
    seen: set[tuple[str, int, str]],
    row,
    match: str,
) -> None:
    key = (row[0], row[1], row[3])
    if key in seen:
        return
    seen.add(key)
    out.append(
        {
            "path": row[0],
            "line": row[1],
            "macro": row[2],
            "statement": row[3],
            "message": row[4],
            "file_hash": row[5],
            "match": match,
        }
    )


def _assert_rank(hit: dict, locations: list[tuple[str, int]]) -> tuple:
    """Prefer text hits, then same-path/near-line hits. Line is never absolute truth."""
    if not locations:
        return (0, 0, hit["path"], hit["line"])
    best_path = 1
    best_dist = 10**9
    for path_hint, line_hint in locations:
        same_path = hit["path"] == path_hint or hit["path"].endswith("/" + path_hint)
        same_base = os.path.basename(hit["path"]) == os.path.basename(path_hint)
        if same_path:
            best_path = min(best_path, 0)
        elif same_base:
            best_path = min(best_path, 1)
        else:
            continue
        best_dist = min(best_dist, abs(int(hit["line"]) - line_hint))
    text_penalty = 0 if hit.get("match") == "text" else 1
    return (text_penalty, best_path, best_dist, hit["path"], hit["line"])


def meta_root() -> str | None:
    """The codebase root the index was built against (for staleness checks)."""
    conn = _connect()
    if conn is None:
        return None
    try:
        row = conn.execute("SELECT value FROM meta WHERE key='root'").fetchone()
        return row[0] if row else None
    except sqlite3.Error:
        return None
    finally:
        conn.close()
