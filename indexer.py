"""Offline symbol index (方案 2, 第一步).

Parses the target C++ codebase with tree-sitter, extracts definitions
(class / struct / enum / function, plus member-function declarations) into a
SQLite table, and builds an FTS5 full-text index over file contents. The index
lets ``tools.find_symbol`` / ``tools.grep_code`` answer precise queries fast
without scanning the whole tree at query time.

The index is a plain SQLite file (config.INDEX_DB_PATH). It is built offline via
``python indexer.py`` (or scripts/index.sh) and queried read-only by index_query.

Design notes:
- Symbols carry file + line + a content hash of the source file, so a future
  staleness check (方案 3) can tell whether a cached fact is still valid.
- C++ only for now (the target is a C++ gameserver). Other languages simply
  aren't indexed; tools fall back to live grep for them.
"""
from __future__ import annotations

import hashlib
import os
import sqlite3

import config

# tree-sitter is only needed at index-build time, imported lazily so the rest of
# the app (and the no-index fallback) never requires it.
_CPP_EXT = {".cpp", ".cc", ".cxx", ".h", ".hpp", ".hh", ".hxx"}

# tree-sitter node types we treat as "definitions" worth indexing.
_DEF_NODE_TYPES = {
    "class_specifier": "class",
    "struct_specifier": "struct",
    "enum_specifier": "enum",
    "union_specifier": "union",
    "function_definition": "function",
}

_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".idea"}


def _file_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", "replace")).hexdigest()


def _iter_cpp_files(root: str):
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS and not d.startswith(".")]
        for fname in files:
            if os.path.splitext(fname)[1].lower() in _CPP_EXT:
                yield os.path.join(dirpath, fname)


def _decl_name(node) -> str | None:
    """Best-effort symbol name for a definition node.

    Handles `name`-field nodes (class/struct/enum) and function_definition,
    whose name hides under a `declarator` chain.
    """
    nm = node.child_by_field_name("name")
    if nm is not None:
        return nm.text.decode("utf-8", "replace")
    d = node.child_by_field_name("declarator")
    seen = 0
    while d is not None and seen < 8:
        if d.type in ("identifier", "field_identifier", "qualified_identifier",
                      "type_identifier", "destructor_name", "operator_name"):
            return d.text.decode("utf-8", "replace")
        nxt = d.child_by_field_name("declarator")
        if nxt is None:
            # function_declarator's name may be a direct child identifier
            for c in d.children:
                if c.type in ("identifier", "field_identifier", "qualified_identifier"):
                    return c.text.decode("utf-8", "replace")
        d = nxt
        seen += 1
    return None


def _extract_symbols(parser, rel_path: str, source: bytes) -> list[tuple]:
    """Return (name, kind, path, line) tuples for definitions + member decls."""
    tree = parser.parse(source)
    out: list[tuple] = []

    def visit(node):
        kind = _DEF_NODE_TYPES.get(node.type)
        if kind:
            name = _decl_name(node)
            if name:
                out.append((name, kind, rel_path, node.start_point[0] + 1))
        # Member function declarations (no body) inside a class/struct body.
        if node.type == "field_declaration":
            for c in node.children:
                if c.type == "function_declarator":
                    name = _decl_name(node)
                    if name:
                        out.append((name, "method", rel_path, node.start_point[0] + 1))
                    break
        for c in node.children:
            visit(c)

    visit(tree.root_node)
    return out


def build(root: str | None = None, db_path: str | None = None, *, verbose: bool = False) -> dict:
    """Build the index. Returns a summary dict (files, symbols)."""
    from tree_sitter import Language, Parser
    import tree_sitter_cpp

    root = os.path.abspath(root or config.TARGET_CODE_PATH)
    db_path = db_path or config.INDEX_DB_PATH
    parser = Parser(Language(tree_sitter_cpp.language()))

    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)  # full rebuild; incremental is a later step
    conn = sqlite3.connect(db_path)
    _init_schema(conn)

    n_files = n_syms = 0
    for abs_path in _iter_cpp_files(root):
        rel = os.path.relpath(abs_path, root)
        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        source = text.encode("utf-8", "replace")
        digest = _file_hash(text)
        conn.execute(
            "INSERT INTO files(path, hash, content) VALUES (?, ?, ?)",
            (rel, digest, text),
        )
        conn.execute(
            "INSERT INTO files_fts(path, content) VALUES (?, ?)", (rel, text)
        )
        syms = _extract_symbols(parser, rel, source)
        if syms:
            conn.executemany(
                "INSERT INTO symbols(name, kind, path, line, file_hash) "
                "VALUES (?, ?, ?, ?, ?)",
                [(n, k, p, ln, digest) for (n, k, p, ln) in syms],
            )
            n_syms += len(syms)
        n_files += 1
        if verbose and n_files % 100 == 0:
            print(f"  indexed {n_files} files, {n_syms} symbols...")

    conn.execute(
        "INSERT INTO meta(key, value) VALUES ('root', ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (root,),
    )
    conn.commit()
    conn.close()
    summary = {"files": n_files, "symbols": n_syms, "db": db_path, "root": root}
    if verbose:
        print(f"[index] done: {summary}")
    return summary


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE files(
            path TEXT PRIMARY KEY,
            hash TEXT NOT NULL,
            content TEXT NOT NULL
        );
        CREATE TABLE symbols(
            name TEXT NOT NULL,
            kind TEXT NOT NULL,
            path TEXT NOT NULL,
            line INTEGER NOT NULL,
            file_hash TEXT NOT NULL
        );
        CREATE INDEX idx_symbols_name ON symbols(name);
        CREATE VIRTUAL TABLE files_fts USING fts5(path, content);
        """
    )


if __name__ == "__main__":
    build(verbose=True)
