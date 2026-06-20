"""Compatibility shim for :mod:`code_agent.interfaces.mcp_server`."""
import sys as _sys
from .interfaces import mcp_server as _impl


if __name__ == "__main__":
    _impl.main()
else:
    _sys.modules[__name__] = _impl
