"""Runtime diagnosis: map a coredump backtrace to code and explain it (方向 F).

MVP scope: parse a gdb-style backtrace, resolve each frame's function to its
definition via the offline symbol index (方案 2), then run the agent over a
diagnosis prompt so it can read the relevant code and reason about the crash.

Frame → code mapping is best-effort:
- Names are demangled (c++filt if available) and stripped of arguments/templates.
- A name may resolve to several definitions (C++ overloads / same name across
  files) — we surface all candidates rather than guess; the agent disambiguates
  using the surrounding frames.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field

# --- backtrace parsing -----------------------------------------------------

# gdb frames look like:
#   #3  0x000055ab in SceneMgr::Update (this=0x..., dt=0.016) at scene/scenemgr.cpp:142
#   #4  GameLoop::tick() at game/loop.cpp:88
#   #5  0x00007f... in ?? ()
_FRAME_RE = re.compile(
    r"^\s*#(?P<num>\d+)\s+"
    r"(?:0x[0-9a-fA-F]+\s+in\s+)?"      # optional address + 'in'
    r"(?P<func>.+?)"                     # function (may include args/templates)
    r"(?:\s+at\s+(?P<file>[^\s:]+):(?P<line>\d+))?"  # optional 'at file:line'
    r"\s*$"
)


@dataclass
class Frame:
    num: int
    func_raw: str
    func: str                      # demangled, args/templates stripped
    file: str | None = None
    line: int | None = None
    candidates: list[dict] = field(default_factory=list)  # index hits

    def short(self) -> str:
        loc = f" at {self.file}:{self.line}" if self.file else ""
        return f"#{self.num} {self.func}{loc}"


def _demangle(name: str) -> str:
    """Demangle a C++ symbol via c++filt if available; else return as-is."""
    if not name or not name.startswith("_Z"):
        return name
    cxxfilt = shutil.which("c++filt")
    if not cxxfilt:
        return name
    try:
        out = subprocess.run(
            [cxxfilt, name], capture_output=True, text=True, timeout=5
        )
        return out.stdout.strip() or name
    except (OSError, subprocess.SubprocessError):
        return name


def _base_function(func: str) -> str:
    """Reduce a frame's function text to a bare symbol name for index lookup.

    'SceneMgr::Update(int, float)' -> 'Update'
    'game::Foo<T>::bar() const'    -> 'bar'
    """
    func = func.strip()
    # Drop argument list and everything after the first '('.
    paren = func.find("(")
    if paren != -1:
        func = func[:paren]
    # Drop template params at the tail of each segment.
    func = re.sub(r"<[^<>]*>", "", func)
    # Take the last :: segment (the method/function name itself).
    if "::" in func:
        func = func.split("::")[-1]
    return func.strip()


def parse_backtrace(text: str) -> list[Frame]:
    """Parse gdb-style backtrace text into Frames. Lines that don't match are
    skipped (e.g. signal headers, '(More stack frames follow...)')."""
    frames: list[Frame] = []
    for raw in text.splitlines():
        m = _FRAME_RE.match(raw)
        if not m:
            continue
        func_raw = m.group("func").strip()
        # '?? ()' and empty frames carry no usable symbol.
        demangled = _demangle(func_raw)
        frames.append(
            Frame(
                num=int(m.group("num")),
                func_raw=func_raw,
                func=demangled,
                file=m.group("file"),
                line=int(m.group("line")) if m.group("line") else None,
            )
        )
    return frames


# --- frame -> code mapping -------------------------------------------------


def _class_of(func: str) -> str | None:
    """Enclosing class/namespace from a frame func, e.g. 'SceneMgr::Update' -> 'SceneMgr'."""
    head = func.split("(")[0]
    head = re.sub(r"<[^<>]*>", "", head)
    parts = [p for p in head.split("::") if p]
    return parts[-2] if len(parts) >= 2 else None


def resolve_frames(frames: list[Frame]) -> list[Frame]:
    """Fill each frame's `candidates` from the symbol index (best-effort).

    When the frame names a class (``SceneMgr::Update``), prefer candidates whose
    file path looks related to that class — this cuts the common-name ambiguity
    (e.g. dozens of ``Update`` methods) down to the likely one(s).
    """
    try:
        import index_query
    except Exception:
        return frames
    for fr in frames:
        base = _base_function(fr.func)
        if base in ("??", ""):
            continue
        hits = index_query.find_symbol(base)
        if not hits:
            continue
        cls = _class_of(fr.func)
        if cls:
            # Prefer files whose name contains the class (case-insensitive),
            # e.g. SceneMgr -> scenemgr.{h,cpp}. Keep all as fallback.
            cls_low = cls.lower()
            preferred = [h for h in hits if cls_low in h["path"].lower()]
            if preferred:
                hits = preferred
        fr.candidates = hits
    return frames


def _format_frames(frames: list[Frame]) -> str:
    """Human/LLM-readable summary of frames + resolved candidates."""
    lines: list[str] = []
    for fr in frames:
        lines.append(fr.short())
        if fr.candidates:
            for c in fr.candidates[:5]:
                lines.append(f"      ↳ {c['kind']} {c['path']}:{c['line']}")
            if len(fr.candidates) > 5:
                lines.append(f"      ↳ ... 另有 {len(fr.candidates) - 5} 个同名候选")
        elif fr.file:
            lines.append("      ↳ (栈帧自带 file:line，可直接 read_file)")
        else:
            lines.append("      ↳ (索引无匹配；可能是库函数/inline/缺符号)")
    return "\n".join(lines)


# --- diagnosis -------------------------------------------------------------

_DIAGNOSIS_PROMPT = """\
下面是一段崩溃栈（backtrace）。请结合代码库分析崩溃根因。

已为每一帧标注了符号索引中的候选定义位置（同名候选可能多个，需要你结合上下
游栈帧判断到底是哪一个）：

{frames}

请按以下步骤分析：
1. 从最可能出错的帧（通常是栈顶非库函数帧）入手，用 read_file 读取对应代码。
2. 若一帧有多个同名候选，结合调用它的上一帧（调用者）判断正确的那个。
3. 给出最可能的崩溃原因（空指针/越界/竞态/断言失败等）及依据（引用 file:line）。
4. 给出排查/修复方向。

原始 backtrace：
{raw}
"""


def diagnose(backtrace: str, *, extra_log: str = "", verbose: bool = False) -> dict:
    """Parse + resolve a backtrace, then let the agent analyze it.

    Returns {"answer", "frames": [...summary...], "resolved": int}.
    """
    import agent

    frames = resolve_frames(parse_backtrace(backtrace))
    resolved = sum(1 for f in frames if f.candidates)
    frames_text = _format_frames(frames) if frames else "(未能解析出任何栈帧)"

    prompt = _DIAGNOSIS_PROMPT.format(frames=frames_text, raw=backtrace.strip())
    if extra_log.strip():
        prompt += f"\n\n相关日志片段：\n{extra_log.strip()}"

    answer = agent.answer(prompt, verbose=verbose)
    return {
        "answer": answer,
        "frames": [f.short() for f in frames],
        "resolved": resolved,
        "total_frames": len(frames),
    }
