"""Compatibility shim for :mod:`code_agent.kb.knowledge_eval`."""
import sys as _sys
from .kb import knowledge_eval as _impl


if __name__ == "__main__":
    raise SystemExit(_impl.main())
else:
    _sys.modules[__name__] = _impl
