"""Interactive command-line tester for the agent.

Usage:
    python -m code_agent.interfaces.cli                 # interactive REPL
    python -m code_agent.interfaces.cli "你的问题"       # one-shot, prints the answer and exits

In the REPL, tool calls are echoed so you can watch the agent's search steps.
"""
import argparse

from .. import config
from ..core import agent


def _one_shot(question: str, *, mode: str | None = None, repo: str | None = None) -> None:
    print(agent.answer(question, verbose=True, mode=mode, repo=repo))


def _repl(*, mode: str | None = None, repo: str | None = None) -> None:
    repo_name = config.resolve_repo_name(repo)
    print("游戏服务器/战斗/客户端/引擎 代码理解服务 — 交互模式")
    with config.use_repo(repo_name):
        print(f"目标代码库[{repo_name}]: {config.current_target_code_path()}")
    print(f"模型: {config.LLM_MODEL}")
    print(f"模式: {mode or config.AGENT_DEFAULT_MODE}")
    print("输入问题后回车；输入 'quit' 或 Ctrl-D 退出。\n")
    while True:
        try:
            question = input("问> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question:
            continue
        if question.lower() in {"quit", "exit", "q"}:
            break
        try:
            print("\n答>", agent.answer(question, verbose=True, mode=mode, repo=repo_name), "\n")
        except Exception as exc:  # keep the REPL alive on errors
            print(f"\n[错误] {exc}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="代码理解服务 CLI")
    parser.add_argument("--mode", default=None, help="plain / technical / edit")
    parser.add_argument("--repo", default=None, help="repo name from CODE_REPOS")
    parser.add_argument("question", nargs="*", help="问题；不传则进入交互模式")
    args = parser.parse_args(argv)
    if args.question:
        _one_shot(" ".join(args.question), mode=args.mode, repo=args.repo)
    else:
        _repl(mode=args.mode, repo=args.repo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
