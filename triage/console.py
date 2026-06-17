"""Console helpers."""

from __future__ import annotations

import sys


def force_utf8_stdio() -> None:
    """Emit UTF-8 regardless of the console code page.

    Windows consoles default to a locale code page (e.g. cp1251/cp437) that
    cannot encode all of our Ukrainian output, which would crash ``print``.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")
