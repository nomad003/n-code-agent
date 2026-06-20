"""Compatibility shim for :mod:`code_agent.retrieval.tools`."""
import sys as _sys
from .retrieval import tools as _impl

_sys.modules[__name__] = _impl
