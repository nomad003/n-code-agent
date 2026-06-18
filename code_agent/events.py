"""Lightweight event model for the custom agent loop.

Modeled on OpenHands' Action/Observation pairing, trimmed for this read-only
Q&A agent: no event bus, no persistence, no subscribers — history is just a
``list[Event]`` the loop appends to. Centralizing "events -> LLM messages" here
(see agent._build_messages) keeps tool_call_id pairing correct in one place.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Action:
    """One tool call the model asked for (the OpenAI tool_call, normalized)."""

    tool_call_id: str
    name: str
    raw_arguments: str  # verbatim JSON string from the model
    # The assistant message that requested this/these calls, kept verbatim so it
    # can be replayed to the API unchanged (preserves provider-specific fields).
    assistant_message: dict = field(default_factory=dict)


@dataclass
class Observation:
    """The result of running an Action's tool (always a string for our tools)."""

    tool_call_id: str
    name: str
    content: str
    is_error: bool = False


# An event is either an Action or an Observation. The running message for the
# user question and the final assistant answer are handled separately by the
# loop; history holds the action/observation interplay.
Event = Action | Observation


def action_key(action: Action) -> tuple[str, str]:
    """Identity used for stuck detection: same tool + same args = same action."""
    return (action.name, action.raw_arguments.strip())


# Per-tool "primary identifier" — the field that, if unchanged across repeated
# calls, signals the model is stuck even when ancillary args vary (different
# path scope, output_mode, context window, etc.). Keyed by tool name; tools not
# listed fall back to the exact-args check in ``action_key``.
_PRIMARY_KEYS = {
    "grep_code": "pattern",
    "read_file": "path",
    "find_symbol": "name",
    "glob": "pattern",
    "list_dir": "path",
    "resolve_frame": "frame",
    "find_log_source": "message",
}


def action_primary_key(action: Action) -> tuple[str, str] | None:
    """Coarse identity: (tool name, primary identifier) — None when unknown."""
    field_name = _PRIMARY_KEYS.get(action.name)
    if not field_name:
        return None
    import json

    try:
        args = json.loads(action.raw_arguments or "{}")
    except (json.JSONDecodeError, TypeError):
        return None
    value = args.get(field_name)
    if not isinstance(value, str):
        return None
    return (action.name, value.strip())
