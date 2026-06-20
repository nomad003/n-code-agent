"""Compatibility shim for :mod:`frontend.assets`."""
import sys as _sys
from frontend import assets as _impl

_sys.modules[__name__] = _impl
