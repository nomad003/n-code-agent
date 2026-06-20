"""Compatibility shim for :mod:`code_agent.kb.assert_knowledge`."""
import sys as _sys
from .kb import assert_knowledge as _impl


if __name__ == "__main__":
    raise SystemExit(_impl.main())
else:
    _sys.modules[__name__] = _impl
