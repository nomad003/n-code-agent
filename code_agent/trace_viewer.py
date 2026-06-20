"""Compatibility shim for :mod:`code_agent.observability.trace_viewer`."""
import sys as _sys
from .observability import trace_viewer as _impl

_sys.modules[__name__] = _impl
