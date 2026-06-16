"""Agent entry point with two interchangeable backends.

``answer()`` dispatches on ``config.AGENT_BACKEND``:

- "custom" (default): the litellm tool-calling loop (``CodeAgent`` below) —
  provider-agnostic, speaks the OpenAI tool-call shape, routes through the proxy.
- "sdk": the Claude Agent SDK loop in ``agent_sdk.py`` (imported lazily so the
  SDK is only required when actually selected).

Both backends reuse the same sandboxed tools in ``tools.py`` and the same
``config.SYSTEM_PROMPT``, and expose the identical ``answer(question)`` contract.

The custom loop borrows three ideas from OpenHands' CodeActAgent, trimmed for a
read-only Q&A agent: an Action/Observation event history with one centralized
"events -> messages" build step, lightweight stuck detection, and LLM retries.
"""
import json

import litellm

import config
import tools
from events import Action, Observation, action_key


def answer(question: str, *, verbose: bool = False) -> str:
    """Answer a question using the configured backend (see config.AGENT_BACKEND).

    First tries an index-only short-circuit (方案 2): precise "where is X
    defined" questions are answered straight from the symbol index, skipping the
    LLM entirely. Anything else runs the full agent loop.
    """
    if config.USE_SHORTCUT:
        import shortcut

        hit = shortcut.try_answer(question)
        if hit is not None:
            if verbose:
                print("  [shortcut] 命中索引，跳过 LLM")
            return hit

    if config.AGENT_BACKEND == "sdk":
        import agent_sdk  # lazy: only import (and require) the SDK when selected

        return agent_sdk.answer(question, verbose=verbose)
    return CodeAgent(verbose=verbose).run(question)


def _routed_model() -> str:
    """Model id routed through the OpenAI-compatible proxy.

    litellm uses the leading provider segment to pick a client; "openai/" forces
    the OpenAI-compatible path so the request goes to ``LLM_API_BASE`` instead of
    litellm trying native Vertex/Bedrock auth. The proxy still receives the real
    model name (e.g. "vertex_ai/gemini-3.5-flash") after the prefix.
    """
    model = config.LLM_MODEL
    return model if model.startswith("openai/") else f"openai/{model}"


class CodeAgent:
    """Tool-calling loop over the sandboxed code-search tools.

    History is a list of Action/Observation events; ``_build_messages`` is the
    single place that turns them into the LLM message list (keeping tool_call_id
    pairing correct). The loop stops on a direct answer, the iteration cap, or
    stuck detection.
    """

    def __init__(self, *, verbose: bool = False):
        self.verbose = verbose
        self.question = ""
        self.history: list = []  # list[Action | Observation]
        self.recalled = ""       # knowledge recalled for this question (方案 3)

    # --- LLM ---------------------------------------------------------------

    def _llm_call(self, *, with_tools: bool = True):
        """One round-trip to the model. Retries transient failures via litellm.

        ``litellm.completion`` does exponential backoff for RateLimit/Timeout/
        InternalServerError when ``num_retries`` is set. ``temperature`` is bumped
        to 1.0 on retries only when it was 0 — works around empty-response loops
        seen with Gemini at temperature 0.
        """
        kwargs = dict(
            model=_routed_model(),
            api_base=config.LLM_API_BASE,
            api_key=config.require_api_key(),
            messages=self._build_messages(with_tools=with_tools),
            temperature=config.LLM_TEMPERATURE,
            timeout=config.LLM_TIMEOUT,
            num_retries=config.LLM_NUM_RETRIES,
        )
        if with_tools:
            kwargs["tools"] = tools.active_schemas()
            kwargs["tool_choice"] = "auto"
        return litellm.completion(**kwargs)

    # --- events -> messages (single source of truth) -----------------------

    def _build_messages(self, *, with_tools: bool) -> list[dict]:
        """Render the system prompt + question + event history as LLM messages.

        Each Action contributes its original assistant message (with the
        tool_call requests); each Observation contributes a matching 'tool'
        message keyed by tool_call_id. This is the one place that has to keep
        request/result pairing consistent.
        """
        system = config.SYSTEM_PROMPT
        if self.recalled:
            system = system + "\n\n" + self.recalled
        messages: list[dict] = [
            {"role": "system", "content": system},
            {"role": "user", "content": self.question},
        ]
        # Observation masking: keep the last OBS_KEEP_FULL tool outputs verbatim;
        # replace older ones with a one-line summary so a long session's context
        # stays bounded. Deterministic, no extra LLM call. 0 = keep everything.
        keep = config.OBS_KEEP_FULL
        observations = [e for e in self.history if isinstance(e, Observation)]
        mask_before = len(observations) - keep if keep > 0 else 0
        obs_index = 0
        seen_assistant_ids: set[int] = set()
        for event in self.history:
            if isinstance(event, Action):
                # One assistant message may carry several tool_calls; emit it once.
                msg_id = id(event.assistant_message)
                if msg_id not in seen_assistant_ids:
                    messages.append(event.assistant_message)
                    seen_assistant_ids.add(msg_id)
            elif isinstance(event, Observation):
                content = event.content
                if obs_index < mask_before:
                    content = self._mask(event)
                obs_index += 1
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": event.tool_call_id,
                        "name": event.name,
                        "content": content,
                    }
                )
        if not with_tools:
            # Final wrap-up turn: nudge the model to answer from what it has.
            messages.append(
                {
                    "role": "user",
                    "content": "已达到工具调用上限，请基于目前收集到的信息给出最终回答。",
                }
            )
        return messages

    @staticmethod
    def _mask(obs: Observation) -> str:
        """One-line stand-in for an older observation (call + size, not content).

        The model still sees that the call happened and roughly how big the
        result was, so it can re-run the tool if it needs the detail again.
        """
        first = obs.content.splitlines()[0] if obs.content else ""
        return f"[省略较早的 {obs.name} 输出，约 {len(obs.content)} 字；首行: {first[:80]}]"

    # --- tool execution ----------------------------------------------------

    def _execute(self, action: Action) -> Observation:
        """Run one tool call, producing an Observation (errors become content)."""
        try:
            args = json.loads(action.raw_arguments or "{}")
        except (json.JSONDecodeError, TypeError):
            return Observation(
                action.tool_call_id,
                action.name,
                f"error: arguments were not valid JSON: {action.raw_arguments!r}",
                is_error=True,
            )
        result = tools.dispatch(action.name, args)
        return Observation(
            action.tool_call_id,
            action.name,
            result,
            is_error=result.startswith("error:"),
        )

    # --- stuck detection ---------------------------------------------------

    def _is_stuck(self) -> bool:
        """True if the last N actions are identical (same tool + same args).

        Catches the common read-only failure mode: re-grepping the same pattern
        or repeatedly hitting the same error. Mirrors OpenHands' repeated-action
        check, trimmed to one rule.
        """
        threshold = config.STUCK_REPEAT_THRESHOLD
        if threshold <= 0:
            return False
        actions = [e for e in self.history if isinstance(e, Action)]
        if len(actions) < threshold:
            return False
        recent = actions[-threshold:]
        first = action_key(recent[0])
        return all(action_key(a) == first for a in recent[1:])

    # --- knowledge flywheel (方案 3) ---------------------------------------

    def _recalled_context(self, question: str) -> str:
        """Knowledge recalled for this question, formatted as a system hint.

        Returns "" when the flywheel is off or nothing is recalled. Stale entries
        are downgraded so the agent treats them as leads to re-verify, not facts.
        """
        if not config.USE_KNOWLEDGE:
            return ""
        try:
            import knowledge

            hits = knowledge.recall(question)
        except Exception:
            return ""
        if not hits:
            return ""
        lines = ["以下是历史问答沉淀的相关线索（仅供参考，请用工具二次核实后再采信）："]
        for h in hits:
            tag = "（⚠️ 引用文件已变更，可能过时，务必重新核实）" if h["stale"] else ""
            refs = ("，涉及 " + ", ".join(h["refs"])) if h["refs"] else ""
            lines.append(f"- 旧问题：{h['question']}{refs}{tag}\n  旧结论：{h['answer'][:500]}")
        return "\n".join(lines)

    def _referenced_files(self) -> list[str]:
        """Repo-relative files the agent consulted (from read_file etc.)."""
        import json as _json

        paths: list[str] = []
        for ev in self.history:
            if isinstance(ev, Action) and ev.name in ("read_file",):
                try:
                    args = _json.loads(ev.raw_arguments or "{}")
                except (ValueError, TypeError):
                    continue
                p = args.get("path")
                if p:
                    paths.append(p)
        return paths

    def _precipitate(self, answer: str) -> None:
        """Store this Q&A into the knowledge base (best-effort, never raises)."""
        if not config.USE_KNOWLEDGE or not answer:
            return
        try:
            import knowledge

            knowledge.store(self.question, answer, self._referenced_files())
        except Exception:
            pass

    # --- main loop ---------------------------------------------------------

    def run(self, question: str) -> str:
        self.question = question
        self.history = []
        self.recalled = self._recalled_context(question)
        answer = self._loop()
        self._precipitate(answer)
        return answer

    def _loop(self) -> str:
        for _ in range(config.MAX_ITERATIONS):
            response = self._llm_call(with_tools=True)
            msg = response.choices[0].message
            tool_calls = getattr(msg, "tool_calls", None)

            # No tool calls → the model is answering directly. We're done.
            if not tool_calls:
                return (msg.content or "").strip()

            assistant_message = msg.model_dump()
            for tc in tool_calls:
                if self.verbose:
                    print(f"  [tool] {tc.function.name}({tc.function.arguments})")
                action = Action(
                    tool_call_id=tc.id,
                    name=tc.function.name,
                    raw_arguments=tc.function.arguments or "{}",
                    assistant_message=assistant_message,
                )
                self.history.append(action)
                self.history.append(self._execute(action))

            if self._is_stuck():
                if self.verbose:
                    print("  [stuck] 检测到重复调用，提前收尾")
                break

        # Iteration cap or stuck: ask for a best-effort answer without tools.
        final = self._llm_call(with_tools=False)
        return (final.choices[0].message.content or "").strip()
