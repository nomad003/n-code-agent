"""Offline symbol index (方案 2, 第一步).

Parses the target C++ codebase with tree-sitter, extracts definitions
(class / struct / enum / function, plus member-function declarations) into a
SQLite table, extracts assert/check sites, and builds FTS5 full-text indexes
over file contents and assert text. The index lets ``tools.find_symbol`` /
``tools.grep_code`` / ``tools.find_assert_context`` answer precise queries fast
without scanning the whole tree at query time.

The index is a plain SQLite file (config.current_index_db_path()). It is built offline via
``python -m code_agent.indexer`` (or scripts/index.sh) and queried read-only by index_query.

Design notes:
- Symbols carry file + line + a content hash of the source file, so a future
  staleness check (方案 3) can tell whether a cached fact is still valid.
- C++ only for now (the target is a C++ gameserver). Other languages simply
  aren't indexed; tools fall back to live grep for them.
"""
from __future__ import annotations

import hashlib
import os
import re
import sqlite3

from .. import config

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
    for dirpath, dirs, files in os.walk(root, followlinks=True):
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


_ASSERT_MACRO_RE = re.compile(
    r"\b(?P<macro>(?:assert|Assert|ASSERT[A-Z0-9_]*|CHECK[A-Z0-9_]*|"
    r"VERIFY[A-Z0-9_]*|ENSURE[A-Z0-9_]*))\s*\("
)


def _paren_balance(text: str) -> int:
    """Rough parenthesis balance, ignoring quoted text."""
    balance = 0
    in_str: str | None = None
    escaped = False
    for ch in text:
        if in_str:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == in_str:
                in_str = None
            continue
        if ch in ("'", '"'):
            in_str = ch
        elif ch == "(":
            balance += 1
        elif ch == ")":
            balance -= 1
    return balance


def _extract_string_literals(text: str) -> list[str]:
    """Extract C/C++ string literal contents from an assert statement."""
    out: list[str] = []
    for m in re.finditer(r'"((?:\\.|[^"\\])*)"', text):
        lit = m.group(1).replace(r"\"", '"').replace(r"\\", "\\")
        if lit:
            out.append(lit)
    return out


def _extract_asserts(rel_path: str, text: str) -> list[tuple]:
    """Return (macro, path, line, statement, message) for assert-like calls."""
    lines = text.splitlines()
    out: list[tuple] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = _ASSERT_MACRO_RE.search(line)
        if not m:
            i += 1
            continue
        start = i
        stmt_lines = [line.strip()]
        balance = _paren_balance(line[m.start():])
        j = i
        while balance > 0 and j + 1 < len(lines) and (j - start) < 8:
            j += 1
            stmt_lines.append(lines[j].strip())
            balance += _paren_balance(lines[j])
        statement = " ".join(part for part in stmt_lines if part)
        statement = re.sub(r"\s+", " ", statement)[:1000]
        message = " ".join(_extract_string_literals(statement))[:500]
        out.append((m.group("macro"), rel_path, start + 1, statement, message))
        i = j + 1
    return out


def build(
    root: str | None = None,
    db_path: str | None = None,
    *,
    repo: str | None = None,
    verbose: bool = False,
) -> dict:
    """Build the index. Returns a summary dict (files, symbols)."""
    from tree_sitter import Language, Parser
    import tree_sitter_cpp

    with config.use_repo(repo):
        root = os.path.abspath(root or config.current_target_code_path())
        db_path = db_path or config.current_index_db_path()
    parser = Parser(Language(tree_sitter_cpp.language()))

    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)  # full rebuild
    conn = sqlite3.connect(db_path)
    _init_schema(conn)

    n_files = n_syms = 0
    for abs_path in _iter_cpp_files(root):
        rel = os.path.relpath(abs_path, root)
        text = _read_text(abs_path)
        if text is None:
            continue
        n_syms += _index_one(conn, parser, rel, text)
        n_files += 1
        if verbose and n_files % 100 == 0:
            print(f"  indexed {n_files} files, {n_syms} symbols...")

    _set_root(conn, root)
    conn.commit()
    conn.close()
    summary = {"files": n_files, "symbols": n_syms, "db": db_path, "root": root}
    if verbose:
        print(f"[index] done: {summary}")
    return summary


def update(
    root: str | None = None,
    db_path: str | None = None,
    *,
    repo: str | None = None,
    verbose: bool = False,
) -> dict:
    """Incrementally sync the index to the current files.

    Re-parses only files whose content hash changed (or are new), and drops rows
    for files that no longer exist. Falls back to a full build if there's no
    existing index yet. Much cheaper than build() when little changed.
    """
    from tree_sitter import Language, Parser
    import tree_sitter_cpp

    with config.use_repo(repo):
        root = os.path.abspath(root or config.current_target_code_path())
        db_path = db_path or config.current_index_db_path()
    if not os.path.isfile(db_path):
        return build(root, db_path, verbose=verbose)

    parser = Parser(Language(tree_sitter_cpp.language()))
    conn = sqlite3.connect(db_path)
    _init_schema(conn)  # idempotent (IF NOT EXISTS)

    # Current on-disk hashes.
    disk: dict[str, str] = {}
    for abs_path in _iter_cpp_files(root):
        rel = os.path.relpath(abs_path, root)
        text = _read_text(abs_path)
        if text is not None:
            disk[rel] = text  # keep text; we may need to re-index
    # Stored hashes.
    stored = {row[0]: row[1] for row in conn.execute("SELECT path, hash FROM files")}

    added = changed = removed = 0
    # Removed: in DB but no longer on disk.
    for rel in set(stored) - set(disk):
        _delete_file(conn, rel)
        removed += 1
    # Added / changed.
    for rel, text in disk.items():
        digest = _file_hash(text)
        if rel not in stored:
            _index_one(conn, parser, rel, text)
            added += 1
        elif stored[rel] != digest:
            _delete_file(conn, rel)
            _index_one(conn, parser, rel, text)
            changed += 1

    _set_root(conn, root)
    conn.commit()
    conn.close()
    summary = {"added": added, "changed": changed, "removed": removed, "db": db_path, "root": root}
    if verbose:
        print(f"[index] incremental: {summary}")
    return summary


def _read_text(abs_path: str) -> str | None:
    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def _index_one(conn: sqlite3.Connection, parser, rel: str, text: str) -> int:
    """Insert one file's rows (files + FTS + symbols). Returns symbol count.

    Caller must ensure no existing rows for ``rel`` remain (delete first on
    update). Returns the number of symbols indexed.
    """
    digest = _file_hash(text)
    conn.execute(
        "INSERT INTO files(path, hash, content) VALUES (?, ?, ?)", (rel, digest, text)
    )
    conn.execute("INSERT INTO files_fts(path, content) VALUES (?, ?)", (rel, text))
    syms = _extract_symbols(parser, rel, text.encode("utf-8", "replace"))
    if syms:
        conn.executemany(
            "INSERT INTO symbols(name, kind, path, line, file_hash) VALUES (?, ?, ?, ?, ?)",
            [(n, k, p, ln, digest) for (n, k, p, ln) in syms],
        )
    for macro, path, line, statement, message in _extract_asserts(rel, text):
        cur = conn.execute(
            "INSERT INTO asserts(macro, path, line, statement, message, file_hash) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (macro, path, line, statement, message, digest),
        )
        conn.execute(
            "INSERT INTO assert_fts(rowid, path, macro, statement, message) "
            "VALUES (?, ?, ?, ?, ?)",
            (cur.lastrowid, path, macro, statement, message),
        )
    return len(syms)


def _delete_file(conn: sqlite3.Connection, rel: str) -> None:
    """Remove all rows for a file (files + FTS + symbols)."""
    conn.execute("DELETE FROM files WHERE path = ?", (rel,))
    conn.execute("DELETE FROM files_fts WHERE path = ?", (rel,))
    conn.execute("DELETE FROM symbols WHERE path = ?", (rel,))
    conn.execute(
        "DELETE FROM assert_fts WHERE rowid IN (SELECT id FROM asserts WHERE path = ?)",
        (rel,),
    )
    conn.execute("DELETE FROM asserts WHERE path = ?", (rel,))


def _set_root(conn: sqlite3.Connection, root: str) -> None:
    conn.execute(
        "INSERT INTO meta(key, value) VALUES ('root', ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (root,),
    )


def _init_schema(conn: sqlite3.Connection) -> None:
    # IF NOT EXISTS so update() can call this on an existing DB harmlessly.
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS files(
            path TEXT PRIMARY KEY,
            hash TEXT NOT NULL,
            content TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS symbols(
            name TEXT NOT NULL,
            kind TEXT NOT NULL,
            path TEXT NOT NULL,
            line INTEGER NOT NULL,
            file_hash TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
        CREATE TABLE IF NOT EXISTS asserts(
            id INTEGER PRIMARY KEY,
            macro TEXT NOT NULL,
            path TEXT NOT NULL,
            line INTEGER NOT NULL,
            statement TEXT NOT NULL,
            message TEXT NOT NULL,
            file_hash TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_asserts_path_line ON asserts(path, line);
        CREATE VIRTUAL TABLE IF NOT EXISTS assert_fts
        USING fts5(path, macro, statement, message);
        CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(path, content);
        """
    )


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Build/update the code index")
    parser.add_argument("--repo", default=None, help="repo name from CODE_REPOS")
    parser.add_argument("-u", "--update", action="store_true", help="incremental update")
    args = parser.parse_args(argv)

    if args.update:
        update(repo=args.repo, verbose=True)
    else:
        build(repo=args.repo, verbose=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
