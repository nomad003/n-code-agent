"""Knowledge precipitation store (方案 3, MVP).

Each answered question is precipitated into a SQLite knowledge base: the
question, the answer, and the source files the agent consulted (with their
content hashes at answer time). Future questions recall related entries as
*leads* — never as ground truth — so the agent re-verifies with tools.

Staleness is the make-or-break mechanism (see roadmap 方案 3): on recall, each
entry's referenced files are re-hashed; if any changed, the entry is flagged
stale so callers can downgrade it to "based on an older version, re-verify".

Storage is a separate DB (config.current_knowledge_db_path()) from the read-only code
index, because knowledge is written incrementally at query time. FTS5 backs
keyword recall; vector/semantic recall is deferred (V3).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3

from . import config


def _connect(*, write: bool) -> sqlite3.Connection:
    path = config.current_knowledge_db_path()
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
        -- trigram tokenizer: substring matching that works for CJK (the default
        -- unicode61 tokenizer treats a whole space-less Chinese run as one token,
        -- so keyword/synonym recall on Chinese questions never fires).
        CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts
            USING fts5(question, answer, content='knowledge', content_rowid='id',
                       tokenize='trigram');
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
    root = config.current_target_code_path()
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


# Lightweight synonym groups so differently-phrased but semantically similar
# questions still recall (a cheap stand-in for vector search until an embedding
# endpoint exists / hit-rate is validated). Each token expands to its group.
_SYNONYMS: list[set[str]] = [
    {"作用", "功能", "职责", "用途", "干嘛", "干什么", "做什么", "用来"},
    {"类", "class", "类型", "结构"},
    {"函数", "方法", "function", "method", "接口"},
    {"字段", "成员", "属性", "变量", "member", "field"},
    {"流程", "逻辑", "过程", "怎么", "如何", "机制"},
    {"调用", "使用", "用法", "call"},
    {"初始化", "创建", "构造", "init"},
]
_SYNONYM_INDEX: dict[str, set[str]] = {}
for _grp in _SYNONYMS:
    for _w in _grp:
        _SYNONYM_INDEX[_w] = _grp


def _shingles(run: str, n: int = 3) -> list[str]:
    """Sliding-window n-grams of a CJK run, matching the trigram tokenizer.

    The trigram FTS tokenizer indexes 3-char windows, so a CJK query term must
    also be broken into 3-char windows to match a substring of a stored answer.
    Runs shorter than n are returned as-is (best effort; may not match).
    """
    if len(run) < n:
        return [run]
    return [run[i : i + n] for i in range(len(run) - n + 1)]


def _fts_or_query(query: str) -> str:
    """Build an FTS5 (trigram) OR-of-terms query from free text.

    Recall should fire when the new question shares keywords/substrings with a
    stored one. We tokenize into Latin words and CJK runs; Latin words are used
    whole, CJK runs are broken into trigram shingles (so '场景管理器的作用' matches a
    stored '...场景管理...'); synonym groups are also shingled in. Every term is
    quoted so punctuation/operators can't break FTS5 syntax.
    """
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]+|[一-鿿]+", query)
    terms: list[str] = []
    for t in tokens:
        if re.match(r"[A-Za-z_]", t):
            if len(t) >= 2:  # single Latin chars too noisy
                terms.append(t)
            # whole-word synonyms (e.g. class/function) still apply
            for syn in _SYNONYM_INDEX.get(t.lower(), ()):
                terms.extend(_shingles(syn) if re.search(r"[一-鿿]", syn) else [syn])
        else:  # CJK run → trigram shingles, plus synonyms of exact-word matches
            terms.extend(_shingles(t))
            for syn in _SYNONYM_INDEX.get(t, ()):
                terms.extend(_shingles(syn) if re.search(r"[一-鿿]", syn) else [syn])
    terms = [t for t in dict.fromkeys(terms) if t.strip()]
    if not terms:
        return ""
    return " OR ".join(f'"{t}"' for t in terms)


def _stale_refs(refs: list[dict]) -> list[str]:
    """Return paths whose content hash no longer matches (changed/deleted)."""
    root = config.current_target_code_path()
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
    if not query or not os.path.isfile(config.current_knowledge_db_path()):
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
    if not os.path.isfile(config.current_knowledge_db_path()):
        return {"entries": 0}
    try:
        conn = _connect(write=False)
        n = conn.execute("SELECT count(*) FROM knowledge").fetchone()[0]
        conn.close()
        return {"entries": n}
    except sqlite3.Error:
        return {"entries": 0}
