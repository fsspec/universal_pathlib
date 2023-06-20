"""Pathlib API extended to use fsspec backends."""
from upath.core import UPath

try:
    from upath._version import __version__
except ImportError:
    __version__ = "not-installed"

__all__ = ["UPath"]
