"""Compatibility shim for :mod:`code_agent.core.question_intent`."""
import sys as _sys
from .core import question_intent as _impl

_sys.modules[__name__] = _impl
