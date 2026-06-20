"""Compatibility shim for :mod:`code_agent.retrieval.repo_profile`."""
import sys as _sys
from .retrieval import repo_profile as _impl


if __name__ == "__main__":
    raise SystemExit(_impl.main())
else:
    _sys.modules[__name__] = _impl
