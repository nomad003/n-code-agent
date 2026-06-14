"""LLM agent loop: tool-calling over the code-search tools via litellm.

The loop is provider-agnostic — it speaks the OpenAI tool-call shape that
litellm normalizes to, and routes every call through the mushigen proxy
configured in ``config.py``. Swapping the model only means changing env vars.
"""
import json

import litellm

import config
import tools


def _routed_model() -> str:
    """Model id routed through the OpenAI-compatible proxy.

    litellm uses the leading provider segment to pick a client; "openai/" forces
    the OpenAI-compatible path so the request goes to ``LLM_API_BASE`` instead of
    litellm trying native Vertex/Bedrock auth. The proxy still receives the real
    model name (e.g. "vertex_ai/gemini-3.5-flash") after the prefix.
    """
    model = config.LLM_MODEL
    return model if model.startswith("openai/") else f"openai/{model}"


def _llm_call(messages: list[dict]):
    """One round-trip to the model, with tools advertised."""
    return litellm.completion(
        model=_routed_model(),
        api_base=config.LLM_API_BASE,
        api_key=config.require_api_key(),
        messages=messages,
        tools=tools.TOOL_SCHEMAS,
        tool_choice="auto",
        temperature=config.LLM_TEMPERATURE,
        timeout=config.LLM_TIMEOUT,
    )


def _run_tool_call(tool_call) -> dict:
    """Execute a single tool call and format it as a 'tool' role message."""
    name = tool_call.function.name
    raw_args = tool_call.function.arguments or "{}"
    try:
        args = json.loads(raw_args)
    except (json.JSONDecodeError, TypeError):
        result = f"error: arguments were not valid JSON: {raw_args!r}"
    else:
        result = tools.dispatch(name, args)
    return {
        "role": "tool",
        "tool_call_id": tool_call.id,
        "name": name,
        "content": result,
    }


def answer(question: str, *, verbose: bool = False) -> str:
    """Run the tool-calling loop until the model produces a final answer."""
    messages: list[dict] = [
        {"role": "system", "content": config.SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    for _ in range(config.MAX_ITERATIONS):
        response = _llm_call(messages)
        msg = response.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None)

        # No tool calls → the model is answering directly. We're done.
        if not tool_calls:
            return (msg.content or "").strip()

        # Record the assistant turn (with its tool-call requests) verbatim.
        messages.append(msg.model_dump())

        for tool_call in tool_calls:
            if verbose:
                print(f"  [tool] {tool_call.function.name}({tool_call.function.arguments})")
            messages.append(_run_tool_call(tool_call))

    # Exhausted the iteration budget: ask for a best-effort final answer.
    messages.append(
        {
            "role": "user",
            "content": "已达到工具调用上限，请基于目前收集到的信息给出最终回答。",
        }
    )
    final = _llm_call(
        [m for m in messages]  # same history; let it answer without more tools
    )
    return (final.choices[0].message.content or "").strip()
