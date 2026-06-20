"""Compatibility shim for :mod:`code_agent.core.agent`."""
import sys as _sys
from .core import agent as _impl

_sys.modules[__name__] = _impl
