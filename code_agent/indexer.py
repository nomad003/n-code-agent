"""Compatibility shim for :mod:`code_agent.retrieval.indexer`."""
import sys as _sys
from .retrieval import indexer as _impl


if __name__ == "__main__":
    raise SystemExit(_impl.main())
else:
    _sys.modules[__name__] = _impl
