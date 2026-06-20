"""Filesystem helpers for the bundled Vue frontend."""

from functools import lru_cache
from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parent / "static"


@lru_cache(maxsize=1)
def app_html() -> str:
    """Return the single-page app shell."""
    return (STATIC_DIR / "app.html").read_text(encoding="utf-8")
