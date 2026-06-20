"""Compatibility shim for :mod:`code_agent.core.events`."""
import sys as _sys
from .core import events as _impl

_sys.modules[__name__] = _impl
