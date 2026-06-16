"""Knowledge precipitation store (方案 3, MVP).

Each answered question is precipitated into a SQLite knowledge base: the
question, the answer, and the source files the agent consulted (with their
content hashes at answer time). Future questions recall related entries as
*leads* — never as ground truth — so the agent re-verifies with tools.

Staleness is the make-or-break mechanism (see roadmap 方案 3): on recall, each
entry's referenced files are re-hashed; if any changed, the entry is flagged
stale so callers can downgrade it to "based on an older version, re-verify".

Storage is a separate DB (config.KNOWLEDGE_DB_PATH) from the read-only code
index, because knowledge is written incrementally at query time. FTS5 backs
keyword recall; vector/semantic recall is deferred (V3).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3

import config


def _connect(*, write: bool) -> sqlite3.Connection:
    path = config.KNOWLEDGE_DB_PATH
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    conn = sqlite3.connect(path)
    if write:
        _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS knowledge(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            refs TEXT NOT NULL DEFAULT '[]',   -- JSON: [{path, hash}]
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts
            USING fts5(question, answer, content='knowledge', content_rowid='id');
        -- keep the FTS index in sync with the base table
        CREATE TRIGGER IF NOT EXISTS knowledge_ai AFTER INSERT ON knowledge BEGIN
            INSERT INTO knowledge_fts(rowid, question, answer)
            VALUES (new.id, new.question, new.answer);
        END;
        CREATE TRIGGER IF NOT EXISTS knowledge_ad AFTER DELETE ON knowledge BEGIN
            INSERT INTO knowledge_fts(knowledge_fts, rowid, question, answer)
            VALUES ('delete', old.id, old.question, old.answer);
        END;
        """
    )


def _hash_file(abs_path: str) -> str | None:
    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
            return hashlib.sha1(fh.read().encode("utf-8", "replace")).hexdigest()
    except OSError:
        return None


def store(question: str, answer: str, ref_paths: list[str]) -> int | None:
    """Precipitate one Q&A into the store. Returns the new row id (or None).

    ref_paths are repo-relative file paths the agent consulted; we record each
    with its current content hash so staleness can be detected on recall.
    """
    question = (question or "").strip()
    answer = (answer or "").strip()
    if not question or not answer:
        return None
    root = config.TARGET_CODE_PATH
    refs = []
    for rel in dict.fromkeys(ref_paths):  # dedupe, preserve order
        h = _hash_file(os.path.join(root, rel))
        if h is not None:
            refs.append({"path": rel, "hash": h})
    try:
        conn = _connect(write=True)
        cur = conn.execute(
            "INSERT INTO knowledge(question, answer, refs) VALUES (?, ?, ?)",
            (question, answer, json.dumps(refs, ensure_ascii=False)),
        )
        conn.commit()
        rid = cur.lastrowid
        conn.close()
        return rid
    except sqlite3.Error:
        return None


def _fts_or_query(query: str) -> str:
    """Build an FTS5 OR-of-terms query from free text.

    Recall should fire when the new question shares *keywords* with a stored
    one, not only on an exact phrase. We split into word/CJK tokens, quote each
    (so punctuation/operators can't break FTS5 syntax), and OR them together.
    """
    # Latin words (>=2 chars) and runs of CJK characters.
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]+|[一-鿿]+", query)
    # Keep CJK runs of length >=2 (single chars are too noisy).
    tokens = [t for t in tokens if len(t) >= 2]
    if not tokens:
        return ""
    return " OR ".join(f'"{t}"' for t in dict.fromkeys(tokens))


def _stale_refs(refs: list[dict]) -> list[str]:
    """Return paths whose content hash no longer matches (changed/deleted)."""
    root = config.TARGET_CODE_PATH
    changed = []
    for r in refs:
        if _hash_file(os.path.join(root, r["path"])) != r["hash"]:
            changed.append(r["path"])
    return changed


def recall(query: str, *, limit: int = 3) -> list[dict]:
    """Recall related knowledge entries for a query (keyword/FTS).

    Each result carries a `stale` flag + `stale_refs` so the caller can present
    it as a lead to re-verify rather than fact. Returns [] if no store/match.
    """
    query = (query or "").strip()
    if not query or not os.path.isfile(config.KNOWLEDGE_DB_PATH):
        return []
    fts_query = _fts_or_query(query)
    if not fts_query:
        return []
    try:
        conn = _connect(write=False)
        rows = conn.execute(
            "SELECT k.id, k.question, k.answer, k.refs "
            "FROM knowledge_fts f JOIN knowledge k ON k.id = f.rowid "
            "WHERE knowledge_fts MATCH ? ORDER BY rank LIMIT ?",
            (fts_query, limit),
        ).fetchall()
        conn.close()
    except sqlite3.Error:
        return []

    out = []
    for rid, q, a, refs_json in rows:
        try:
            refs = json.loads(refs_json)
        except (json.JSONDecodeError, TypeError):
            refs = []
        stale = _stale_refs(refs)
        out.append(
            {
                "id": rid,
                "question": q,
                "answer": a,
                "refs": [r["path"] for r in refs],
                "stale": bool(stale),
                "stale_refs": stale,
            }
        )
    return out


def stats() -> dict:
    """Quick counts for diagnostics/eval (total entries)."""
    if not os.path.isfile(config.KNOWLEDGE_DB_PATH):
        return {"entries": 0}
    try:
        conn = _connect(write=False)
        n = conn.execute("SELECT count(*) FROM knowledge").fetchone()[0]
        conn.close()
        return {"entries": n}
    except sqlite3.Error:
        return {"entries": 0}
