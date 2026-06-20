"""Compatibility shim for :mod:`code_agent.evals.evaluate`."""
import sys as _sys
from .evals import evaluate as _impl


if __name__ == "__main__":
    raise SystemExit(_impl.main())
else:
    _sys.modules[__name__] = _impl
