"""Pathlib API extended to use fsspec backends."""
import sys

try:
    from upath._version import __version__
except ImportError:
    __version__ = "not-installed"

if sys.version_info >= (3, 12):
    import upath.core312plus as core
else:
    import upath.core as core

UPath = core.UPath

__all__ = ["UPath"]
