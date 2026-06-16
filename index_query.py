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
    try:
        # FTS5 MATCH wants a query string; quote it as a phrase to treat the
        # user's text literally (avoids FTS operator surprises).
        fts_query = '"' + query.replace('"', '""') + '"'
        file_rows = conn.execute(
            "SELECT path, content FROM files_fts WHERE files_fts MATCH ? LIMIT 500",
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
