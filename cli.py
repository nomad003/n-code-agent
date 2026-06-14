"""Interactive command-line tester for the agent.

Usage:
    python3 cli.py                 # interactive REPL
    python3 cli.py "你的问题"       # one-shot, prints the answer and exits

In the REPL, tool calls are echoed so you can watch the agent's search steps.
"""
import sys

import agent
import config


def _one_shot(question: str) -> None:
    print(agent.answer(question, verbose=True))


def _repl() -> None:
    print("游戏服务器/战斗/客户端/引擎 代码理解服务 — 交互模式")
    print(f"目标代码库: {config.TARGET_CODE_PATH}")
    print(f"模型: {config.LLM_MODEL}")
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
            print("\n答>", agent.answer(question, verbose=True), "\n")
        except Exception as exc:  # keep the REPL alive on errors
            print(f"\n[错误] {exc}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        _one_shot(" ".join(sys.argv[1:]))
    else:
        _repl()
