"""Compatibility shim for :mod:`code_agent.interfaces.cli`."""
import sys as _sys
from .interfaces import cli as _impl


if __name__ == "__main__":
    raise SystemExit(_impl.main())
else:
    _sys.modules[__name__] = _impl
