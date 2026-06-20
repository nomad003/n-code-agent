"""Compatibility shim for :mod:`code_agent.kb.module_knowledge`."""
import sys as _sys
from .kb import module_knowledge as _impl

_sys.modules[__name__] = _impl
