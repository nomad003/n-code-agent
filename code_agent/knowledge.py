"""Compatibility shim for :mod:`code_agent.kb.knowledge`."""
import sys as _sys
from .kb import knowledge as _impl

_sys.modules[__name__] = _impl
