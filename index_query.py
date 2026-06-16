"""Read-only queries against the offline index (方案 2).

Used by tools.find_symbol / tools.grep_code when an index exists. All functions
are defensive: if the DB is missing/unusable they return None so the caller can
fall back to live filesystem scanning. The index is opened read-only per call
(cheap for SQLite; keeps the module stateless and fork/thread-safe).
"""
from __future__ import annotations

import os
import sqlite3

import config


def available() -> bool:
    """True if an index DB exists and the index is enabled."""
    return config.USE_INDEX and os.path.isfile(config.INDEX_DB_PATH)


def _connect() -> sqlite3.Connection | None:
    if not available():
        return None
    try:
        # immutable=1: open read-only, assume the file won't change under us.
        uri = f"file:{config.INDEX_DB_PATH}?mode=ro"
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
