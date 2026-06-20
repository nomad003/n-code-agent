"""Compatibility shim for :mod:`code_agent.core.agent_sdk`."""
import sys as _sys
from .core import agent_sdk as _impl

_sys.modules[__name__] = _impl
