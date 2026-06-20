"""Compatibility shim for :mod:`code_agent.retrieval.index_query`."""
import sys as _sys
from .retrieval import index_query as _impl

_sys.modules[__name__] = _impl
