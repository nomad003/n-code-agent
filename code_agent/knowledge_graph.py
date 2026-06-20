"""Compatibility shim for :mod:`code_agent.kb.knowledge_graph`."""
import sys as _sys
from .kb import knowledge_graph as _impl

_sys.modules[__name__] = _impl
