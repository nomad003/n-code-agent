#!/usr/bin/env python3
"""Smoke-test the configured custom LLM proxy.

This is intentionally not part of the default pytest suite because it performs
a real network call and consumes proxy quota. It loads `.env` before importing
project config, then sends a minimal litellm chat completion request.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


def _sanitize(text: str) -> str:
    key = os.environ.get("LLM_API_KEY", "")
    if key:
        text = text.replace(key, "***")
    return text


def _routed_model(model: str) -> str:
    return model if model.startswith("openai/") else f"openai/{model}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check custom litellm proxy connectivity.")
    parser.add_argument("--timeout", type=float, default=30.0, help="request timeout seconds")
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=0,
        help="completion token budget; 0 means omit max_tokens",
    )
    parser.add_argument("--prompt", default="请只输出 PONG", help="minimal prompt to send")
    args = parser.parse_args()

    os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
    _load_dotenv(PROJECT_ROOT / ".env")

    from code_agent import config
    import litellm

    model = _routed_model(config.LLM_MODEL)
    has_key = bool(config.LLM_API_KEY)
    print(f"[llm-smoke] backend={config.AGENT_BACKEND}")
    print(f"[llm-smoke] api_base={config.LLM_API_BASE}")
    print(f"[llm-smoke] model={config.LLM_MODEL}")
    print(f"[llm-smoke] routed_model={model}")
    print(f"[llm-smoke] api_key={'present' if has_key else 'missing'}")
    if not has_key:
        print("[llm-smoke] failed: LLM_API_KEY is missing", file=sys.stderr)
        return 2

    started = time.monotonic()
    try:
        kwargs = dict(
            model=model,
            api_base=config.LLM_API_BASE,
            api_key=config.LLM_API_KEY,
            messages=[{"role": "user", "content": args.prompt}],
            temperature=0,
            timeout=args.timeout,
            num_retries=0,
        )
        if args.max_tokens > 0:
            kwargs["max_tokens"] = args.max_tokens
        response = litellm.completion(**kwargs)
    except Exception as exc:
        elapsed = time.monotonic() - started
        print(
            f"[llm-smoke] failed after {elapsed:.2f}s: {type(exc).__name__}: "
            f"{_sanitize(str(exc))}",
            file=sys.stderr,
        )
        return 1

    elapsed = time.monotonic() - started
    message = response.choices[0].message
    content = (getattr(message, "content", "") or "").strip()
    finish_reason = getattr(response.choices[0], "finish_reason", "")
    if not content:
        print(f"[llm-smoke] failed: empty response finish_reason={finish_reason}", file=sys.stderr)
        return 1
    print(f"[llm-smoke] ok elapsed={elapsed:.2f}s")
    print(f"[llm-smoke] finish_reason={finish_reason}")
    print(f"[llm-smoke] response={content[:200]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
