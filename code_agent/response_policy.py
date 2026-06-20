"""Compatibility shim for :mod:`code_agent.core.response_policy`."""
import sys as _sys
from .core import response_policy as _impl

_sys.modules[__name__] = _impl
