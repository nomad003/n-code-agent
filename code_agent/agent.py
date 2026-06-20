"""Agent entry point with two interchangeable backends.

``answer()`` dispatches on ``config.AGENT_BACKEND``:

- "custom" (default): the litellm tool-calling loop (``CodeAgent`` below) —
  provider-agnostic, speaks the OpenAI tool-call shape, routes through the proxy.
- "sdk": the Claude Agent SDK loop in ``code_agent.agent_sdk`` (imported lazily so the
  SDK is only required when actually selected).

Both backends reuse the same sandboxed tools in ``code_agent.tools`` and the same
``config.SYSTEM_PROMPT``, and expose the identical ``answer(question)`` contract.

The custom loop borrows three ideas from OpenHands' CodeActAgent, trimmed for a
read-only Q&A agent: an Action/Observation event history with one centralized
"events -> messages" build step, lightweight stuck detection, and LLM retries.
"""
import json

import litellm

from . import config
from . import knowledge_graph
from . import llm_trace
from . import module_knowledge
from . import operation_modes
from . import question_intent
from . import response_policy
from . import tools
from .events import Action, Observation, action_key, action_primary_key


def answer(
    question: str,
    *,
    verbose: bool = False,
    mode: str | None = None,
    repo: str | None = None,
    question_type: str | None = None,
) -> str:
    """Answer a question using the configured backend (see config.AGENT_BACKEND).

    First tries an index-only short-circuit (方案 2): precise "where is X
    defined" questions are answered straight from the symbol index, skipping the
    LLM entirely. Anything else runs the full agent loop.
    """
    with config.use_repo(repo):
        return _answer_in_repo(
            question, verbose=verbose, mode=mode, question_type=question_type
        )


def _answer_in_repo(
    question: str,
    *,
    verbose: bool = False,
    mode: str | None = None,
    question_type: str | None = None,
) -> str:
    resolved_mode = operation_modes.resolve(
        mode, default=config.AGENT_DEFAULT_MODE, allowed=config.AGENT_ALLOWED_MODES
    )
    trace = llm_trace.LLMTrace(
        question=question, mode=resolved_mode, backend=config.AGENT_BACKEND
    )
    try:
        if config.USE_SHORTCUT:
            from . import shortcut

            hit = shortcut.try_answer(question)
            if hit is not None:
                if verbose:
                    print("  [shortcut] 命中索引，跳过 LLM")
                answer_text = response_policy.enforce(hit, mode=resolved_mode)
                trace.write("shortcut", answer=answer_text)
                trace.write("request_end", answer=answer_text)
                return answer_text

        if config.AGENT_BACKEND == "sdk":
            from . import agent_sdk  # lazy: only import (and require) the SDK when selected

            answer_text = response_policy.enforce(
                agent_sdk.answer(
                    question, verbose=verbose, mode=resolved_mode, trace=trace
                ),
                mode=resolved_mode,
            )
        else:
            answer_text = response_policy.enforce(
                CodeAgent(
                    verbose=verbose,
                    mode=resolved_mode,
                    question_type=question_type,
                    trace=trace,
                ).run(question),
                mode=resolved_mode,
            )
        trace.write("request_end", answer=answer_text)
        return answer_text
    except Exception as exc:
        trace.write(
            "request_error",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise


def _routed_model() -> str:
    """Model id routed through the OpenAI-compatible proxy.

    litellm uses the leading provider segment to pick a client; "openai/" forces
    the OpenAI-compatible path so the request goes to ``LLM_API_BASE`` instead of
    litellm trying native Vertex/Bedrock auth. The proxy still receives the real
    model name (e.g. "vertex_ai/gemini-3.5-flash") after the prefix.
    """
    model = config.LLM_MODEL
    return model if model.startswith("openai/") else f"openai/{model}"


def _looks_like_answer(text: str) -> bool:
    """Heuristic: is this assistant text substantial enough to use as the answer?

    The model often emits "Let me check X next." style narration alongside its
    tool calls; we don't want to ship that as the final answer when the loop
    runs out of iterations. Require a minimum length AND some structural signal
    (sentence terminator or a colon followed by content) so a stray short line
    can't bypass the wrap-up call.
    """
    if not text or len(text) < 120:
        return False
    return any(p in text for p in ("。", ".", "：", ":", "\n"))


def _unique_nonempty(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


class CodeAgent:
    """Tool-calling loop over the sandboxed code-search tools.

    History is a list of Action/Observation events; ``_build_messages`` is the
    single place that turns them into the LLM message list (keeping tool_call_id
    pairing correct). The loop stops on a direct answer, the iteration cap, or
    stuck detection.
    """

    def __init__(
        self,
        *,
        verbose: bool = False,
        mode: str = "plain",
        question_type: str | None = None,
        trace: llm_trace.LLMTrace | None = None,
    ):
        self.verbose = verbose
        self.mode = operation_modes.normalize(mode)
        self.question_type = question_intent.normalize(question_type)
        self.trace = trace
        self.round = 0
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
        messages = self._build_messages(with_tools=with_tools)
        self.round += 1
        round_no = self.round
        kwargs = dict(
            model=_routed_model(),
            api_base=config.LLM_API_BASE,
            api_key=config.require_api_key(),
            messages=messages,
            temperature=config.LLM_TEMPERATURE,
            timeout=config.LLM_TIMEOUT,
            num_retries=config.LLM_NUM_RETRIES,
        )
        if with_tools:
            kwargs["tools"] = tools.active_schemas()
            kwargs["tool_choice"] = "auto"
        if self.trace:
            self.trace.write(
                "llm_request",
                round=round_no,
                with_tools=with_tools,
                model=_routed_model(),
                messages=messages,
                tools=kwargs.get("tools", []),
                tool_choice=kwargs.get("tool_choice"),
                temperature=config.LLM_TEMPERATURE,
                timeout=config.LLM_TIMEOUT,
                num_retries=config.LLM_NUM_RETRIES,
            )
        try:
            response = litellm.completion(**kwargs)
        except Exception as exc:
            if self.trace:
                self.trace.write(
                    "llm_error",
                    round=round_no,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
            raise
        if self.trace:
            msg = response.choices[0].message
            usage = getattr(response, "usage", None)
            self.trace.write(
                "llm_response",
                round=round_no,
                message=msg.model_dump() if hasattr(msg, "model_dump") else msg,
                usage=usage.model_dump() if hasattr(usage, "model_dump") else usage,
            )
        return response

    # --- events -> messages (single source of truth) -----------------------

    def _build_messages(self, *, with_tools: bool) -> list[dict]:
        """Render the system prompt + question + event history as LLM messages.

        Each Action contributes its original assistant message (with the
        tool_call requests); each Observation contributes a matching 'tool'
        message keyed by tool_call_id. This is the one place that has to keep
        request/result pairing consistent.
        """
        system = config.system_prompt_for_mode(self.mode)
        system = system + "\n\n" + question_intent.prompt(self.question, self.question_type)
        try:
            from . import repo_profile

            profile_text = repo_profile.format_for_prompt()
        except Exception:
            profile_text = ""
        if profile_text:
            system = system + "\n\n" + profile_text
        if config.CODE_KNOWLEDGE_MAP_ENABLED:
            try:
                from . import knowledge_graph

                graph_text = knowledge_graph.format_map_for_prompt(
                    self.question, limit=config.CODE_KNOWLEDGE_MAP_MAX_CARDS
                )
            except Exception:
                graph_text = ""
            if graph_text:
                system = system + "\n\n" + graph_text
        module_text = module_knowledge.format_for_prompt(self.question)
        if module_text:
            system = system + "\n\n" + module_text
        if self.recalled:
            system = system + "\n\n" + self.recalled
        # Mark the static prefix (system + initial user question) for prompt
        # caching when the provider supports it. Anthropic / Bedrock honor
        # ``cache_control``; non-Anthropic backends (Gemini through the proxy)
        # silently ignore it, so this is free upside when applicable and a
        # no-op elsewhere. Toggle off via ``LLM_PROMPT_CACHE=0``.
        if config.LLM_PROMPT_CACHE:
            system_msg = {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": system,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            }
        else:
            system_msg = {"role": "system", "content": system}
        messages: list[dict] = [
            system_msg,
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
        """Stable one-line stand-in for an older observation.

        Earlier we embedded the byte size + first-line preview here. Both vary
        per call, so the masked text changed across rounds even though the
        underlying observation didn't — which silently broke the LLM proxy's
        prefix cache for everything after it. Keep this string a pure function
        of the tool name so a round-2 mask string == round-7 mask string.
        """
        return f"[省略较早的 {obs.name} 输出，如需可重新调用]"

    # --- tool execution ----------------------------------------------------

    def _execute(self, action: Action) -> Observation:
        """Run one tool call, producing an Observation (errors become content)."""
        try:
            args = json.loads(action.raw_arguments or "{}")
        except (json.JSONDecodeError, TypeError):
            content = f"error: arguments were not valid JSON: {action.raw_arguments!r}"
            if self.trace:
                self.trace.write(
                    "tool_result",
                    tool_call_id=action.tool_call_id,
                    name=action.name,
                    raw_arguments=action.raw_arguments,
                    result=content,
                    is_error=True,
                )
            return Observation(
                action.tool_call_id,
                action.name,
                content,
                is_error=True,
            )
        result = tools.dispatch(action.name, args)
        if self.trace:
            self.trace.write(
                "tool_result",
                tool_call_id=action.tool_call_id,
                name=action.name,
                arguments=args,
                result=result,
                is_error=result.startswith("error:"),
            )
        return Observation(
            action.tool_call_id,
            action.name,
            result,
            is_error=result.startswith("error:"),
        )

    # --- stuck detection ---------------------------------------------------

    def _is_stuck(self) -> bool:
        """True if the loop appears to be spinning. Three rules, OR-combined:

        1. Last N actions are exactly identical (same tool + same args).
        2. Last N actions share the same tool + primary identifier — e.g.
           ``grep_code`` with the same ``pattern`` but varying ``path`` /
           ``context`` / ``output_mode``. Catches the "keep tweaking the same
           search" loop that rule 1 misses.
        3. Last N observations are all errors. Model is thrashing on feedback
           it doesn't know how to fix; further turns won't help.
        """
        threshold = config.STUCK_REPEAT_THRESHOLD
        if threshold <= 0:
            return False
        actions = [e for e in self.history if isinstance(e, Action)]
        if len(actions) >= threshold:
            recent = actions[-threshold:]
            # Rule 1: identical args.
            first_exact = action_key(recent[0])
            if all(action_key(a) == first_exact for a in recent[1:]):
                return True
            # Rule 2: same tool + primary identifier across the window.
            first_primary = action_primary_key(recent[0])
            if first_primary and all(
                action_primary_key(a) == first_primary for a in recent[1:]
            ):
                return True
        # Rule 3: all recent observations are errors.
        observations = [e for e in self.history if isinstance(e, Observation)]
        if len(observations) >= threshold:
            recent_obs = observations[-threshold:]
            if all(o.is_error for o in recent_obs):
                return True
        return False

    # --- knowledge flywheel (方案 3) ---------------------------------------

    def _recalled_context(self, question: str) -> str:
        """Knowledge recalled for this question, formatted as a system hint.

        Returns "" when the flywheel is off or nothing is recalled. Stale entries
        are downgraded so the agent treats them as leads to re-verify, not facts.
        """
        if not config.USE_KNOWLEDGE:
            return ""
        try:
            from . import knowledge

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
            from . import knowledge

            knowledge.store(self.question, answer, self._referenced_files())
        except Exception:
            pass

    # --- main loop ---------------------------------------------------------

    def run(self, question: str) -> str:
        self.question = question
        self.history = []
        self.recalled = self._recalled_context(question)
        answer = self._loop()
        answer = self._augment_answer(answer)
        self._precipitate(answer)
        return answer

    def _augment_answer(self, answer: str) -> str:
        footer = self._knowledge_evidence_footer(answer)
        if not footer:
            return answer
        return f"{(answer or '').rstrip()}\n\n{footer}".strip()

    def _knowledge_evidence_footer(self, answer: str) -> str:
        try:
            cards = knowledge_graph.load_cards(
                config.current_repo().name,
                include_common=True,
            )
        except Exception:
            return ""
        scored = [
            (knowledge_graph.score_card(self.question, card), card)
            for card in cards
        ]
        scored = [(score, card) for score, card in scored if score > 0]
        if not scored:
            return ""
        scored.sort(
            key=lambda item: (
                knowledge_graph.is_reference_card(item[1]),
                -item[0],
                item[1].id,
            )
        )
        selected = [card for _score, card in scored[:3]]
        files = self._referenced_files()
        symbols: list[str] = []
        logs: list[str] = []
        asserts: list[str] = []
        card_ids: list[str] = []
        for card in selected:
            card_ids.append(card.id)
            files.extend(card.field_list("resource"))
            symbols.extend(card.field_list("symbols"))
            logs.extend(card.field_list("logs"))
            asserts.extend(card.field_list("asserts"))
        files = _unique_nonempty(files)[:8]
        symbols = _unique_nonempty(symbols)[:10]
        logs = _unique_nonempty(logs)[:6]
        asserts = _unique_nonempty(asserts)[:6]
        card_ids = _unique_nonempty(card_ids)[:3]
        if not any((files, symbols, logs, asserts, card_ids)):
            return ""
        lines = ["## 关键线索"]
        if card_ids:
            lines.append(f"- 知识卡: {', '.join(card_ids)}")
        if files:
            lines.append(f"- 关键文件: {', '.join(files)}")
        if symbols:
            lines.append(f"- 关键符号: {', '.join(symbols)}")
        if logs:
            lines.append(f"- 日志短语: {', '.join(logs)}")
        if asserts:
            lines.append(f"- 断言: {', '.join(asserts)}")
        return "\n".join(lines)

    def _loop(self) -> str:
        last_assistant_text = ""
        for _ in range(config.MAX_ITERATIONS):
            response = self._llm_call(with_tools=True)
            msg = response.choices[0].message
            tool_calls = getattr(msg, "tool_calls", None)

            # No tool calls → the model is answering directly. We're done.
            if not tool_calls:
                self._progress("answer")
                return (msg.content or "").strip()

            # The model frequently emits a narration text block alongside its
            # tool_calls ("Based on what I've seen so far: ..."). Track the most
            # recent one — if we run out of iterations we can use it instead of
            # paying for an extra wrap-up turn.
            text = (msg.content or "").strip()
            if text:
                last_assistant_text = text

            assistant_message = msg.model_dump()
            self._progress(
                "tools",
                tool_calls=[
                    (tc.function.name, tc.function.arguments or "{}") for tc in tool_calls
                ],
            )
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
                self._progress("stuck")
                if self.verbose:
                    print("  [stuck] 检测到重复调用，提前收尾")
                break

        # Iteration cap or stuck. If the model already produced a substantial
        # text block in its most recent turn, reuse it — the wrap-up call would
        # just rephrase the same content for ~3-5k extra prompt tokens. We only
        # accept text that looks like a real answer (>=120 chars, includes a
        # full stop or colon) so short narrations don't slip through.
        if _looks_like_answer(last_assistant_text):
            self._progress("reuse-text")
            return last_assistant_text
        final = self._llm_call(with_tools=False)
        return (final.choices[0].message.content or "").strip()

    def _progress(self, kind: str, *, tool_calls=None) -> None:
        """One-line stderr progress so MCP/serve operators can see the loop tick.

        Deliberately uses stderr (verbose=True still prints to stdout) so backend
        log tailers see it without touching the user-facing answer pipe.
        """
        import sys

        round_no = self.round  # incremented by _llm_call before this is called
        if kind == "answer":
            print(
                f"[agent round {round_no}/{config.MAX_ITERATIONS}] direct answer",
                file=sys.stderr,
                flush=True,
            )
            return
        if kind == "stuck":
            print(
                f"[agent round {round_no}/{config.MAX_ITERATIONS}] stuck — finalizing",
                file=sys.stderr,
                flush=True,
            )
            return
        # tools
        calls = tool_calls or []

        def _short(args: str) -> str:
            s = args.replace("\n", " ").strip()
            return s if len(s) <= 80 else s[:77] + "…"

        rendered = ", ".join(f"{n}({_short(a)})" for n, a in calls) or "(none)"
        print(
            f"[agent round {round_no}/{config.MAX_ITERATIONS}] {len(calls)} tool_call(s): {rendered}",
            file=sys.stderr,
            flush=True,
        )
