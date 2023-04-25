"""Pathlib API extended to use fsspec backends."""
__version__ = "0.0.23"

from upath.core import UPath
from upath.errors import ignore_default_warning


__all__ = ["UPath", "ignore_default_warning"]
