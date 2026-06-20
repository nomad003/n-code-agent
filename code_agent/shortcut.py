"""Compatibility shim for :mod:`code_agent.retrieval.shortcut`."""
import sys as _sys
from .retrieval import shortcut as _impl

_sys.modules[__name__] = _impl
