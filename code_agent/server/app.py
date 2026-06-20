"""Compatibility shim for :mod:`server.app`."""
import sys as _sys
from server import app as _impl

_sys.modules[__name__] = _impl
