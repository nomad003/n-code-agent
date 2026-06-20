"""Compatibility shim for :mod:`server.app`."""
import sys as _sys
from server import app as _impl

if __name__ == "__main__":
    import uvicorn

    from .. import config

    uvicorn.run(_impl.app, host=config.SERVICE_HOST, port=config.SERVICE_PORT)
else:
    _sys.modules[__name__] = _impl
