"""Compatibility shim for :mod:`code_agent.observability.llm_trace`."""
import sys as _sys
from .observability import llm_trace as _impl

_sys.modules[__name__] = _impl
