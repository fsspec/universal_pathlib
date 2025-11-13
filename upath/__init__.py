"""Pathlib API extended to use fsspec backends."""

from __future__ import annotations

from typing import TYPE_CHECKING

try:
    from upath._version import __version__
except ImportError:
    __version__ = "not-installed"

if TYPE_CHECKING:
    from upath.core import UnsupportedOperation
    from upath.core import UPath

__all__ = ["UPath", "UnsupportedOperation"]


def __getattr__(name):
    if name == "UPath":
        from upath.core import UPath

        globals()["UPath"] = UPath
        return UPath
    elif name == "UnsupportedOperation":
        from upath.core import UnsupportedOperation

        globals()["UnsupportedOperation"] = UnsupportedOperation
        return UnsupportedOperation
    else:
        raise AttributeError(f"module {__name__} has no attribute {name}")
