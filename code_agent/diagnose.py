"""Compatibility shim for :mod:`code_agent.diagnostics.diagnose`."""
import sys as _sys
from .diagnostics import diagnose as _impl

_sys.modules[__name__] = _impl
