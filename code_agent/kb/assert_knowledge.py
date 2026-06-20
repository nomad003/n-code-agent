"""Structured assert knowledge generated from target code.

The offline index can locate assert/check lines. This module adds a maintained
diagnosis layer on top: what user-facing problem the assert represents, why it
usually fires, and which checks/fixes should be tried first.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from typing import Iterable

from .. import config


CATALOG_FILE = "assert-catalog.json"
DEFAULT_EXCLUDES = (
    "**/.git/**",
    "**/build/**",
    "**/cmake-build-*/**",
    "**/protocol/**",
    "**/test/**",
    "**/*test*",
    "**/swigwin-*/**",
)
SOURCE_EXTS = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"}
ASSERT_RE = re.compile(
    r"\b(?P<macro>(?:assert|Assert|ASSERT[A-Z0-9_]*|CHECK[A-Z0-9_]*|"
    r"VERIFY[A-Z0-9_]*|ENSURE[A-Z0-9_]*))\s*\("
)
SOURCE_LOC_RE = re.compile(
    r"(?P<path>[\w./\\-]+\.(?:cpp|cc|cxx|c|h|hpp|hh|hxx))[:(](?P<line>\d+)"
)
FUNCTION_RE = re.compile(
    r"^\s*(?:[\w:<>,~*&\[\]\s]+\s+)?(?P<name>[A-Za-z_~][\w:~]*)\s*"
    r"\([^;{}]*\)\s*(?:const\s*)?(?:noexcept\s*)?(?:override\s*)?(?:\{|$)"
)


@dataclass(frozen=True)
class AssertEntry:
    id: str
    repo: str
    source: str
    path: str
    line: int
    macro: str
    statement: str
    condition: str
    message: str
    function: str
    module: str
    category: str
    problem: str
    context: str
    why: str
    fix_steps: list[str]
    match_terms: list[str]
    context_lines: list[str]
    file_hash: str

    @classmethod
    def from_dict(cls, data: dict) -> "AssertEntry":
        return cls(
            id=str(data.get("id", "")),
            repo=str(data.get("repo", "")),
            source=str(data.get("source", "")),
            path=str(data.get("path", "")),
            line=int(data.get("line") or 0),
            macro=str(data.get("macro", "")),
            statement=str(data.get("statement", "")),
            condition=str(data.get("condition", "")),
            message=str(data.get("message", "")),
            function=str(data.get("function", "")),
            module=str(data.get("module", "")),
            category=str(data.get("category", "")),
            problem=str(data.get("problem", "")),
            context=str(data.get("context", "")),
            why=str(data.get("why", "")),
            fix_steps=list(data.get("fix_steps") or []),
            match_terms=list(data.get("match_terms") or []),
            context_lines=list(data.get("context_lines") or []),
            file_hash=str(data.get("file_hash", "")),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "repo": self.repo,
            "source": self.source,
            "path": self.path,
            "line": self.line,
            "macro": self.macro,
            "statement": self.statement,
            "condition": self.condition,
            "message": self.message,
            "function": self.function,
            "module": self.module,
            "category": self.category,
            "problem": self.problem,
            "context": self.context,
            "why": self.why,
            "fix_steps": self.fix_steps,
            "match_terms": self.match_terms,
            "context_lines": self.context_lines,
            "file_hash": self.file_hash,
        }


def catalog_path(repo: str | None = None) -> str:
    repo_name = repo or config.current_repo().name
    return os.path.join(
        config.PROJECT_ROOT,
        "docs",
        "code-knowledge",
        repo_name,
        "asserts",
        CATALOG_FILE,
    )


def load_catalog(repo: str | None = None) -> list[AssertEntry]:
    path = catalog_path(repo)
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return []
    return list(_load_catalog_cached(path, mtime))


@lru_cache(maxsize=16)
def _load_catalog_cached(path: str, mtime: float) -> tuple[AssertEntry, ...]:
    try:
        data = json.loads(open(path, "r", encoding="utf-8").read())
    except (OSError, json.JSONDecodeError):
        return ()
    rows = data.get("asserts", data if isinstance(data, list) else [])
    return tuple(AssertEntry.from_dict(row) for row in rows if isinstance(row, dict))


def match(
    query: str,
    *,
    repo: str | None = None,
    limit: int = 4,
    min_score: int = 10,
) -> list[tuple[int, AssertEntry]]:
    """Return relevant assert playbooks for a user log/question."""
    query = (query or "").strip()
    if not query:
        return []
    q_low = query.lower()
    q_terms = _terms(query)
    locations = _source_locations(query)
    scored: list[tuple[int, AssertEntry]] = []
    for entry in load_catalog(repo):
        score = _score_entry(entry, q_low, q_terms, locations)
        if score >= min_score:
            scored.append((score, entry))
    scored.sort(key=lambda item: (-item[0], item[1].path, item[1].line))
    return scored[:limit]


def lookup(
    path: str,
    line: int,
    *,
    repo: str | None = None,
    tolerance: int = 3,
) -> list[AssertEntry]:
    path = (path or "").replace("\\", "/").lstrip("./")
    out: list[AssertEntry] = []
    for entry in load_catalog(repo):
        same_path = entry.path == path or entry.path.endswith("/" + path)
        same_base = os.path.basename(entry.path) == os.path.basename(path)
        if (same_path or same_base) and abs(entry.line - int(line)) <= tolerance:
            out.append(entry)
    out.sort(key=lambda item: (abs(item.line - int(line)), item.path, item.line))
    return out


def format_for_prompt(query: str, *, limit: int | None = None) -> str:
    """Format matched assert playbooks for system-prompt injection."""
    if not config.ASSERT_KNOWLEDGE_ENABLED:
        return ""
    limit = limit or config.ASSERT_KNOWLEDGE_MAX_ITEMS
    hits = [entry for _score, entry in match(query, limit=limit)]
    return format_entries(hits, query=query)


def format_for_hits(hits: Iterable[dict], *, query: str = "") -> str:
    """Format playbooks corresponding to index hits from find_assert_context."""
    if not config.ASSERT_KNOWLEDGE_ENABLED:
        return ""
    entries: list[AssertEntry] = []
    seen: set[str] = set()
    for hit in hits:
        for entry in lookup(str(hit.get("path", "")), int(hit.get("line") or 0)):
            if entry.id not in seen:
                seen.add(entry.id)
                entries.append(entry)
                break
    if not entries and query:
        entries = [entry for _score, entry in match(query)]
    return format_entries(entries, query=query)


def format_entries(entries: Iterable[AssertEntry], *, query: str = "") -> str:
    selected = list(entries)[: config.ASSERT_KNOWLEDGE_MAX_ITEMS]
    if not selected:
        return ""
    lines = [
        "已命中的 Assert 知识（结构化排障线索；仍需结合当前代码上下文确认）："
    ]
    if query:
        lines.append(f"用户输入摘要: {_one_line(query, 160)}")
    for entry in selected:
        lines.append("")
        lines.append(
            f"- {entry.path}:{entry.line} [{entry.macro}]"
            f" function={entry.function or '-'} category={entry.category}"
        )
        lines.append(f"  对应问题: {entry.problem}")
        lines.append(f"  上下文: {entry.context}")
        lines.append(f"  为什么出问题: {entry.why}")
        if entry.message:
            lines.append(f"  运行日志/提示: {entry.message}")
        if entry.condition:
            lines.append(f"  断言条件: {entry.condition}")
        if entry.match_terms:
            lines.append(f"  匹配关键词: {', '.join(entry.match_terms[:8])}")
        if entry.fix_steps:
            lines.append("  排查/解决:")
            for step in entry.fix_steps[:5]:
                lines.append(f"    - {step}")
    return "\n".join(lines)


def build_catalog(
    sources: list[tuple[str, str]],
    *,
    repo: str,
    excludes: Iterable[str] = DEFAULT_EXCLUDES,
) -> list[AssertEntry]:
    entries: list[AssertEntry] = []
    for source_name, root in sources:
        root = os.path.abspath(root)
        for path in _iter_source_files(root, excludes):
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            logical_path = f"{source_name}/{rel}"
            try:
                text = open(path, "r", encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            entries.extend(
                _entries_from_text(
                    text,
                    repo=repo,
                    source=source_name,
                    logical_path=logical_path,
                )
            )
    entries.sort(key=lambda item: (item.path, item.line, item.macro))
    return entries


def write_catalog(
    entries: list[AssertEntry],
    *,
    repo: str,
    output_dir: str | None = None,
    split_markdown: bool = True,
) -> dict:
    out_dir = output_dir or os.path.dirname(catalog_path(repo))
    os.makedirs(out_dir, exist_ok=True)
    data = {
        "repo": repo,
        "generated_at": date.today().isoformat(),
        "count": len(entries),
        "asserts": [entry.to_dict() for entry in entries],
    }
    json_path = os.path.join(out_dir, CATALOG_FILE)
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    md_paths: list[str] = []
    if split_markdown:
        groups: dict[str, list[AssertEntry]] = {}
        for entry in entries:
            groups.setdefault(_card_group(entry.path), []).append(entry)
        index_path = os.path.join(out_dir, "index.md")
        with open(index_path, "w", encoding="utf-8") as fh:
            fh.write(_render_index_card(repo, entries, groups))
        md_paths.append(index_path)
        for group, group_entries in sorted(groups.items()):
            path = os.path.join(out_dir, f"{group}.md")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(_render_group_card(repo, group, group_entries))
            md_paths.append(path)
    return {"json": json_path, "markdown": md_paths, "count": len(entries)}


def _entries_from_text(
    text: str,
    *,
    repo: str,
    source: str,
    logical_path: str,
) -> list[AssertEntry]:
    lines = text.splitlines()
    file_hash = hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()
    entries: list[AssertEntry] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = ASSERT_RE.search(line)
        if not m or _is_comment_match(line, m.start()):
            i += 1
            continue
        start = i
        stmt_lines = [line.strip()]
        balance = _paren_balance(line[m.start() :])
        j = i
        while balance > 0 and j + 1 < len(lines) and (j - start) < 8:
            j += 1
            stmt_lines.append(lines[j].strip())
            balance += _paren_balance(lines[j])
        statement = re.sub(r"\s+", " ", " ".join(stmt_lines)).strip()[:1000]
        condition = _first_argument(statement, m.group("macro"))
        context_lines = _context_lines(lines, start)
        message = _message_for_assert(statement, context_lines)
        function = _enclosing_function(lines, start)
        module = _module_of(logical_path)
        category = _category(logical_path, m.group("macro"), condition, message)
        problem = _problem(logical_path, m.group("macro"), condition, message, category)
        context = _context(logical_path, function, message, context_lines)
        why = _why(category, condition, message)
        steps = _fix_steps(category, logical_path, condition, message)
        match_terms = _match_terms(
            logical_path, m.group("macro"), condition, message, function, problem
        )
        entry_id = _entry_id(logical_path, start + 1, m.group("macro"), statement)
        entries.append(
            AssertEntry(
                id=entry_id,
                repo=repo,
                source=source,
                path=logical_path,
                line=start + 1,
                macro=m.group("macro"),
                statement=statement,
                condition=condition,
                message=message,
                function=function,
                module=module,
                category=category,
                problem=problem,
                context=context,
                why=why,
                fix_steps=steps,
                match_terms=match_terms,
                context_lines=context_lines,
                file_hash=file_hash,
            )
        )
        i = j + 1
    return entries


def _iter_source_files(root: str, excludes: Iterable[str]) -> Iterable[str]:
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
        rel_dir = "" if rel_dir == "." else rel_dir
        dirnames[:] = [
            d
            for d in sorted(dirnames)
            if not _excluded(os.path.join(rel_dir, d).replace(os.sep, "/") + "/", excludes)
        ]
        for filename in sorted(filenames):
            ext = os.path.splitext(filename)[1].lower()
            if ext not in SOURCE_EXTS:
                continue
            rel = os.path.join(rel_dir, filename).replace(os.sep, "/")
            if _excluded(rel, excludes):
                continue
            yield os.path.join(dirpath, filename)


def _excluded(rel: str, excludes: Iterable[str]) -> bool:
    rel = rel.replace(os.sep, "/").lstrip("./")
    return any(fnmatch.fnmatch(rel, pattern) for pattern in excludes)


def _is_comment_match(line: str, start: int) -> bool:
    prefix = line[:start]
    stripped = prefix.strip()
    if stripped.startswith("//"):
        return True
    comment_pos = prefix.rfind("/*")
    close_pos = prefix.rfind("*/")
    return comment_pos != -1 and comment_pos > close_pos


def _paren_balance(text: str) -> int:
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


def _first_argument(statement: str, macro: str) -> str:
    idx = statement.find(macro)
    if idx < 0:
        return ""
    start = statement.find("(", idx)
    if start < 0:
        return ""
    args = statement[start + 1 : _matching_paren(statement, start)]
    parts = _split_top_level(args)
    return _one_line(parts[0], 240) if parts else ""


def _matching_paren(text: str, start: int) -> int:
    balance = 0
    in_str: str | None = None
    escaped = False
    for idx in range(start, len(text)):
        ch = text[idx]
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
            if balance == 0:
                return idx
    return len(text)


def _split_top_level(args: str) -> list[str]:
    parts: list[str] = []
    start = 0
    balance = 0
    in_str: str | None = None
    escaped = False
    for idx, ch in enumerate(args):
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
        elif ch in "([{":
            balance += 1
        elif ch in ")]}":
            balance -= 1
        elif ch == "," and balance == 0:
            parts.append(args[start:idx].strip())
            start = idx + 1
    tail = args[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def _string_literals(text: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(r'"((?:\\.|[^"\\])*)"', text or ""):
        lit = m.group(1).replace(r"\"", '"').replace(r"\\", "\\")
        if lit:
            out.append(lit)
    return out


def _context_lines(lines: list[str], start: int, radius: int = 5) -> list[str]:
    begin = max(0, start - radius)
    end = min(len(lines), start + radius + 1)
    return [
        f"{idx + 1}: {_one_line(lines[idx].strip(), 220)}"
        for idx in range(begin, end)
        if lines[idx].strip()
    ]


def _message_for_assert(statement: str, context_lines: list[str]) -> str:
    literals = _string_literals(statement)
    for line in context_lines:
        if re.search(
            r"\b(UnitLogErr|LogErr|LogError|LogWarn|LogFatal|Fatal|Error|Warn)\b",
            line,
        ):
            literals.extend(_string_literals(line))
    return _one_line(" | ".join(_unique(literals)), 300)


def _enclosing_function(lines: list[str], start: int) -> str:
    window_start = max(0, start - 80)
    for idx in range(start, window_start - 1, -1):
        line = lines[idx].strip()
        if not line or line.startswith(("//", "#")):
            continue
        m = FUNCTION_RE.match(line)
        if m:
            name = m.group("name")
            if name not in {"if", "for", "while", "switch", "return"}:
                return name
    return ""


def _module_of(path: str) -> str:
    parts = path.split("/")
    if not parts:
        return ""
    if parts[0] == "gameserver" and len(parts) >= 2:
        return "/".join(parts[:3]) if parts[1] == "unit" and len(parts) >= 3 else "/".join(parts[:2])
    if parts[0] == "XEcsLib" and len(parts) >= 3:
        return "/".join(parts[:4]) if parts[2] == "ecs" and len(parts) >= 4 else "/".join(parts[:3])
    return "/".join(parts[:2])


def _category(path: str, macro: str, condition: str, message: str) -> str:
    text = " ".join([path, macro, condition, message]).lower()
    if any(s in text for s in ("not found", "not find", "template", "config", "conf", "row", "table")):
        return "config_or_table_missing"
    if any(s in text for s in ("null", "nullptr", "nil", "none", "punit", "pcaster", "ptarget")):
        return "null_or_missing_object"
    if any(s in text for s in ("index", "idx", "size", "count", "range", "<", ">=", "max")):
        return "bounds_or_count_invalid"
    if any(s in text for s in ("valid(e)", "has(e)", "entity", "component", "xecs")):
        return "ecs_entity_or_component_invalid"
    if any(s in text for s in ("pos", "vector", "nan", "flt_epsilon", "ratio", "zero")):
        return "numeric_or_position_invalid"
    if any(s in text for s in ("state", "stage", "skill")):
        return "state_or_skill_invalid"
    if condition.strip() in {"false", "0"} or "false &&" in condition:
        return "unexpected_branch"
    if "return" in macro.lower():
        return "precondition_failed"
    return "invariant_failed"


def _problem(path: str, macro: str, condition: str, message: str, category: str) -> str:
    base = {
        "config_or_table_missing": "配置/表数据缺失或字段不一致，导致代码拿不到必须的行数据。",
        "null_or_missing_object": "关键对象为空或未创建，后续逻辑无法继续。",
        "bounds_or_count_invalid": "索引、数量或范围不满足代码约束，可能越界或数据结构不完整。",
        "ecs_entity_or_component_invalid": "ECS entity/component 状态不一致，访问了不存在或无效的实体/组件。",
        "numeric_or_position_invalid": "坐标、比例或数值非法，可能是负坐标、NaN、0 比例或物理数据异常。",
        "state_or_skill_invalid": "状态机或技能数据不符合当前流程要求。",
        "unexpected_branch": "执行到了代码认为不应该到达的分支。",
        "precondition_failed": "函数前置条件失败，当前调用参数或对象状态不满足要求。",
        "invariant_failed": "代码内部不变量被破坏。",
    }.get(category, "断言条件失败。")
    detail = message or condition or macro
    return f"{base} 触发点 `{path}`，关键条件 `{_one_line(detail, 160)}`。"


def _context(path: str, function: str, message: str, context_lines: list[str]) -> str:
    parts = [f"文件 `{path}`"]
    if function:
        parts.append(f"函数 `{function}`")
    if message:
        parts.append(f"附近日志 `{_one_line(message, 140)}`")
    elif context_lines:
        parts.append(f"附近代码 `{_one_line(context_lines[min(len(context_lines)-1, 5)], 140)}`")
    return "，".join(parts) + "。"


def _why(category: str, condition: str, message: str) -> str:
    subject = _one_line(message or condition or "断言条件", 160)
    why_map = {
        "config_or_table_missing": "运行时数据引用了配置表中不存在的 ID、模板、技能或字段组合。",
        "null_or_missing_object": "调用链传入了空指针，或对象生命周期/创建流程没有完成。",
        "bounds_or_count_invalid": "数据数量和代码期望不一致，或索引计算越过有效范围。",
        "ecs_entity_or_component_invalid": "Entity 已释放、未注册、generation 不匹配，或组件没有按流程添加。",
        "numeric_or_position_invalid": "上游传入非法数值，常见是坐标未初始化、比例为 0、NaN 或负值。",
        "state_or_skill_invalid": "当前状态、技能类型或配置不允许进入该分支。",
        "unexpected_branch": "枚举值、类型分支或配置组合没有被当前代码支持。",
        "precondition_failed": "调用方没有满足函数入口约束，宏通常会提前返回。",
        "invariant_failed": "对象内部状态被破坏，需要向上追踪最后一次写入。",
    }
    return f"{why_map.get(category, '断言表达式求值失败。')} 直接线索：`{subject}`。"


def _fix_steps(category: str, path: str, condition: str, message: str) -> list[str]:
    common = [
        f"先用日志中的文件/函数定位到 `{path}`，不要只相信运行时行号；行号可能因版本漂移不准。",
        f"读取断言前后 30-80 行，确认 `{_one_line(condition or message, 120)}` 由谁赋值或返回。",
    ]
    specific = {
        "config_or_table_missing": [
            "核对日志里的 ID、模板 ID、技能名、表名和当前发布的配置版本。",
            "检查配置加载是否成功、fallback 表是否存在，以及客户端/服务器配置是否同版本。",
            "修复缺失行或字段后重载/重新发布配置，再用同一 ID 复现验证。",
        ],
        "null_or_missing_object": [
            "沿调用链检查对象创建、查找和释放路径，确认是否提前销毁或查找 key 不一致。",
            "补充上游判空和错误日志；如果对象必须存在，应修复创建/注册流程。",
        ],
        "bounds_or_count_invalid": [
            "打印索引、size/count、配置数组长度和来源 ID，确认是哪侧数据越界。",
            "修正配置数量、循环边界或索引计算；必要时增加非法数据拦截。",
        ],
        "ecs_entity_or_component_invalid": [
            "确认 entity id/generation 是否仍有效，组件是否已 add，系统执行顺序是否正确。",
            "检查 remove/destroy 和 view 遍历是否并发修改同一容器。",
        ],
        "numeric_or_position_invalid": [
            "打印上游坐标/比例/向量来源，检查初始化、单位转换和物理碰撞数据。",
            "修正非法数据源；对外部输入增加范围校验。",
        ],
        "state_or_skill_invalid": [
            "检查当前状态机状态、技能配置、AI 技能名和 SkillList 查表结果。",
            "确认状态切换时序和技能类型是否符合代码分支要求。",
        ],
        "unexpected_branch": [
            "确认枚举、类型或配置值是否新增但代码没有处理。",
            "补齐对应分支，或修正配置不要落到未支持类型。",
        ],
        "precondition_failed": [
            "检查调用方为什么传入不满足条件的参数；宏返回值通常会改变后续业务结果。",
            "如果是可恢复错误，补充上游日志并返回明确错误码。",
        ],
        "invariant_failed": [
            "追踪对象字段最后一次写入位置，确认是否有重入、并发或生命周期问题。",
            "补充最小复现日志，记录关键 ID、状态和配置版本。",
        ],
    }.get(category, [])
    return common + specific


def _match_terms(
    path: str,
    macro: str,
    condition: str,
    message: str,
    function: str,
    problem: str,
) -> list[str]:
    terms: list[str] = [macro, path, os.path.basename(path)]
    if function:
        terms.append(function)
    for text in (condition, message, problem):
        if text:
            terms.append(_one_line(text, 120))
            terms.extend(_terms(text)[:12])
    return _unique(t for t in terms if len(t) >= 2)[:32]


def _score_entry(
    entry: AssertEntry,
    q_low: str,
    q_terms: list[str],
    locations: list[tuple[str, int]],
) -> int:
    score = 0
    for path_hint, line_hint in locations:
        same_path = entry.path == path_hint or entry.path.endswith("/" + path_hint)
        same_base = os.path.basename(entry.path) == os.path.basename(path_hint)
        if same_path or same_base:
            dist = abs(entry.line - line_hint)
            score += max(15, 90 - min(dist, 80)) if same_path else max(8, 45 - min(dist, 40))
    hay = " ".join(
        [
            entry.path,
            entry.macro,
            entry.statement,
            entry.condition,
            entry.message,
            entry.function,
            entry.problem,
            " ".join(entry.match_terms),
        ]
    ).lower()
    for term in q_terms:
        if term in hay:
            score += 7 if len(term) >= 8 else 3
    for phrase in entry.match_terms:
        low = phrase.lower()
        if len(low) >= 8 and low in q_low:
            score += 14
    if entry.message and entry.message.lower() in q_low:
        score += 30
    if entry.macro.lower() in q_low:
        score += 5
    if "check cond" in q_low and entry.macro.startswith("CHECK"):
        score += 8
    if "false" in q_low and entry.condition.strip() in {"false", "0"}:
        score += 10
    return score


def _source_locations(query: str) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for m in SOURCE_LOC_RE.finditer(query or ""):
        path = m.group("path").replace("\\", "/").lstrip("./")
        try:
            line = int(m.group("line"))
        except ValueError:
            continue
        item = (path, line)
        if item not in out:
            out.append(item)
    return out


def _terms(text: str) -> list[str]:
    terms = re.findall(r"[A-Za-z_][A-Za-z0-9_:./-]+|[一-鿿]{2,}", text or "")
    out: list[str] = []
    for term in terms:
        low = term.lower().strip("./")
        if len(low) >= 2:
            out.append(low)
        if re.fullmatch(r"[一-鿿]{3,}", term):
            for size in (2, 3, 4):
                for i in range(0, len(term) - size + 1):
                    out.append(term[i : i + size])
    return _unique(out)


def _entry_id(path: str, line: int, macro: str, statement: str) -> str:
    stem = re.sub(r"[^a-zA-Z0-9]+", "-", path).strip("-").lower()
    digest = hashlib.sha1(statement.encode("utf-8", errors="ignore")).hexdigest()[:8]
    return f"{stem}-{line}-{macro.lower()}-{digest}"


def _card_group(path: str) -> str:
    module = _module_of(path)
    group = module.replace("/", "-")
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", group).strip("-").lower() or "misc"


def _render_index_card(
    repo: str,
    entries: list[AssertEntry],
    groups: dict[str, list[AssertEntry]],
) -> str:
    macros = _unique(entry.macro for entry in entries)
    resources = _unique(entry.module for entry in entries)
    lines = [
        "---",
        "type: Reference",
        "title: Assert 排障索引",
        "description: gameserver 与 XEcsLib 核心代码 Assert/CHECK 结构化排障目录。",
        f"repo: {repo}",
        "module: asserts",
        "resource: " + ", ".join(resources[:16]),
        "tags: assert, check, outage_log, crash, diagnostic",
        "symbols: " + ", ".join(_unique(e.function for e in entries if e.function)[:24]),
        "logs: Check cond, ASSERT, failed, Error Exit",
        "asserts: " + ", ".join(macros),
        "question_types: crash_stack, outage_log",
        f"updated_at: {date.today().isoformat()}",
        "---",
        "",
        "# Assert 排障索引",
        "",
        "## 卡片说明",
        "",
        "| 项 | 内容 |",
        "| --- | --- |",
        f"| 覆盖范围 | gameserver 与 XEcsLib 核心代码，共 {len(entries)} 个 Assert/CHECK 条目。 |",
        "| 用途 | 用户贴 `Check cond`、`ASSERT`、`failed`、`Error Exit` 或 `file:line` 日志时，先匹配本索引，再读代码上下文确认。 |",
        "| 生成物 | `assert-catalog.json` 是运行时匹配源；本目录 Markdown 是可视化维护卡。 |",
        "",
        "## 分组",
        "",
        "| 分组 | 数量 | 卡片 |",
        "| --- | ---: | --- |",
    ]
    for group, group_entries in sorted(groups.items()):
        lines.append(f"| `{group}` | {len(group_entries)} | [{group}.md]({group}.md) |")
    lines.extend(
        [
            "",
            "## 回答要求",
            "",
            "当用户日志命中某个 Assert 条目时，答案必须包含：",
            "",
            "- 对应问题：这个断言代表哪类业务/数据问题。",
            "- 上下文：文件、函数、附近日志、触发条件。",
            "- 为什么出问题：配置缺失、对象为空、ECS 状态不一致、越界、非法坐标等。",
            "- 怎么解决：按排查顺序给出配置、数据、调用链或代码修复动作。",
            "- 行号说明：运行时行号可能漂移，必须结合函数、日志短语和代码上下文确认。",
            "",
        ]
    )
    return "\n".join(lines)


def _render_group_card(repo: str, group: str, entries: list[AssertEntry]) -> str:
    title = f"Assert 排障 - {group}"
    resources = _unique(entry.path for entry in entries)
    macros = _unique(entry.macro for entry in entries)
    logs = _unique(entry.message for entry in entries if entry.message)
    symbols = _unique(entry.function for entry in entries if entry.function)
    lines = [
        "---",
        "type: Code Playbook",
        f"title: {title}",
        f"description: {group} 模块 Assert/CHECK 的问题、上下文、原因和解决步骤。",
        f"repo: {repo}",
        f"module: asserts/{group}",
        "resource: " + ", ".join(resources[:12]),
        "tags: assert, check, outage_log, crash, " + group.replace("-", ", "),
        _frontmatter_list("symbols", symbols[:24]),
        _frontmatter_list("logs", logs[:12]),
        "asserts: " + ", ".join(macros),
        "question_types: crash_stack, outage_log, feature_impl, config_impl",
        "part_of: index.md",
        f"updated_at: {date.today().isoformat()}",
        "---",
        "",
        f"# {title}",
        "",
        "## 卡片说明",
        "",
        "| 项 | 内容 |",
        "| --- | --- |",
        f"| 分组 | `{group}` |",
        f"| 条目数 | {len(entries)} |",
        "| 使用方式 | 用户贴日志后，优先匹配 `assert-catalog.json`；本卡用于人工复核和图谱展示。 |",
        "",
        "## Assert 条目",
        "",
    ]
    for entry in entries:
        lines.extend(_render_entry(entry))
    return "\n".join(lines).rstrip() + "\n"


def _render_entry(entry: AssertEntry) -> list[str]:
    lines = [
        f"### `{entry.path}:{entry.line}` `{entry.macro}`",
        "",
        "| 字段 | 内容 |",
        "| --- | --- |",
        f"| ID | `{entry.id}` |",
        f"| 函数 | `{entry.function or '-'}` |",
        f"| 类型 | `{entry.category}` |",
        f"| 条件 | `{_escape_cell(entry.condition)}` |",
        f"| 日志/提示 | `{_escape_cell(entry.message or '-')}` |",
        f"| 对应问题 | {entry.problem} |",
        f"| 上下文 | {entry.context} |",
        f"| 为什么出问题 | {entry.why} |",
        "",
        "排查/解决：",
        "",
    ]
    lines.extend(f"- {step}" for step in entry.fix_steps)
    if entry.context_lines:
        lines.extend(["", "附近代码：", "", "```text"])
        lines.extend(entry.context_lines)
        lines.append("```")
    lines.append("")
    return lines


def _escape_cell(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


def _frontmatter_list(name: str, values: list[str]) -> str:
    joined = ", ".join(values)
    return f"{name}: {joined}" if joined else f"{name}:"


def _one_line(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def _unique(items: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        key = str(item).strip()
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build structured assert knowledge")
    parser.add_argument("--repo", default="marvel", help="knowledge repo name")
    parser.add_argument(
        "--source",
        action="append",
        required=True,
        help="source mapping in name=/abs/path form; repeatable",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="output dir, default docs/code-knowledge/<repo>/asserts",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="additional fnmatch exclude pattern relative to each source root",
    )
    args = parser.parse_args(argv)
    sources: list[tuple[str, str]] = []
    for item in args.source:
        name, sep, path = item.partition("=")
        if not sep or not name.strip() or not path.strip():
            raise SystemExit("--source must be name=/abs/path")
        sources.append((name.strip(), os.path.abspath(path.strip())))
    entries = build_catalog(
        sources,
        repo=args.repo,
        excludes=tuple(DEFAULT_EXCLUDES) + tuple(args.exclude),
    )
    result = write_catalog(entries, repo=args.repo, output_dir=args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
