"""Compatibility shim for :mod:`code_agent.core.operation_modes`."""
import sys as _sys
from .core import operation_modes as _impl

_sys.modules[__name__] = _impl
