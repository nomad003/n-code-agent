"""Repository profile / navigation cache.

The profile is a cheap, deterministic summary of a target repo: top-level
directories, file-type distribution, likely docs/config/build entrypoints, and
large module directories. Build it offline per repo and inject it as orientation
for the agent so broad questions do not start by re-enumerating the tree.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime

from . import config

_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".idea"}
_BINARY_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".gz", ".tar",
    ".so", ".dll", ".exe", ".bin", ".o", ".a", ".pyc", ".jar", ".class",
    ".mp3", ".wav", ".mp4", ".ttf", ".woff", ".woff2",
}
_ENTRY_NAMES = {
    "README", "README.md", "CMakeLists.txt", "Makefile", "BUILD", "WORKSPACE",
    "package.json", "pyproject.toml", "go.mod", "Cargo.toml",
}


def build(*, repo: str | None = None, max_files: int = 50000) -> dict:
    """Build and persist the profile for one configured repo."""
    with config.use_repo(repo) as selected:
        root = config.current_target_code_path()
        profile_path = config.current_profile_path()
        profile = _scan(root, selected.name, max_files=max_files)
        os.makedirs(os.path.dirname(profile_path) or ".", exist_ok=True)
        with open(profile_path, "w", encoding="utf-8") as fh:
            json.dump(profile, fh, ensure_ascii=False, indent=2)
        return profile


def load(*, repo: str | None = None) -> dict | None:
    """Load the current repo profile, if it exists."""
    with config.use_repo(repo):
        path = config.current_profile_path()
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, json.JSONDecodeError):
            return None


def format_for_prompt(profile: dict | None = None) -> str:
    """Compact profile text suitable for system-prompt injection."""
    profile = profile if profile is not None else load()
    if not profile:
        return ""
    lines = [
        "已缓存的代码库导航（作为检索起点；具体结论仍需用工具核实）：",
        f"- repo: {profile.get('repo')} ({profile.get('root')})",
    ]
    dirs = profile.get("top_dirs") or []
    if dirs:
        lines.append("- 顶层目录: " + ", ".join(d["path"] for d in dirs[:20]))
    modules = profile.get("modules") or []
    if modules:
        lines.append(
            "- 常用/大模块候选: "
            + ", ".join(f"{m['path']}({m['files']} files)" for m in modules[:12])
        )
    entries = profile.get("entrypoints") or []
    if entries:
        lines.append("- 入口/说明文件: " + ", ".join(entries[:20]))
    exts = profile.get("extensions") or []
    if exts:
        lines.append(
            "- 主要文件类型: "
            + ", ".join(f"{e['ext']}={e['files']}" for e in exts[:10])
        )
    return "\n".join(lines)


def _scan(root: str, repo_name: str, *, max_files: int) -> dict:
    ext_counts: Counter[str] = Counter()
    dir_counts: Counter[str] = Counter()
    entrypoints: list[str] = []
    total_files = 0
    total_dirs = 0

    top_dirs = []
    try:
        for name in sorted(os.listdir(root)):
            if name.startswith(".") or name in _SKIP_DIRS:
                continue
            full = os.path.join(root, name)
            if os.path.isdir(full):
                top_dirs.append({"path": name, "kind": "dir"})
            elif os.path.isfile(full):
                top_dirs.append({"path": name, "kind": "file"})
    except OSError:
        top_dirs = []

    for dirpath, dirs, files in os.walk(root, followlinks=True):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS and not d.startswith(".")]
        total_dirs += 1
        rel_dir = os.path.relpath(dirpath, root)
        rel_dir = "." if rel_dir == "." else rel_dir.replace(os.sep, "/")
        if rel_dir != ".":
            dir_counts[rel_dir] += 0
        for fname in files:
            if total_files >= max_files:
                break
            if fname.startswith("."):
                continue
            ext = os.path.splitext(fname)[1].lower() or "<no_ext>"
            if ext in _BINARY_EXT:
                continue
            total_files += 1
            ext_counts[ext] += 1
            if rel_dir != ".":
                dir_counts[rel_dir] += 1
            if fname in _ENTRY_NAMES or fname.upper().startswith("README"):
                rel = os.path.relpath(os.path.join(dirpath, fname), root)
                entrypoints.append(rel.replace(os.sep, "/"))

    modules = [
        {"path": path, "files": n}
        for path, n in dir_counts.most_common(30)
        if path != "." and n > 0
    ]
    return {
        "repo": repo_name,
        "root": root,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "total_files_scanned": total_files,
        "total_dirs_scanned": total_dirs,
        "truncated": total_files >= max_files,
        "top_dirs": top_dirs[:100],
        "modules": modules,
        "entrypoints": sorted(dict.fromkeys(entrypoints))[:100],
        "extensions": [
            {"ext": ext, "files": n} for ext, n in ext_counts.most_common(30)
        ],
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build repository navigation profile")
    parser.add_argument("--repo", default=None, help="repo name from CODE_REPOS")
    args = parser.parse_args()
    result = build(repo=args.repo)
    print(format_for_prompt(result))
