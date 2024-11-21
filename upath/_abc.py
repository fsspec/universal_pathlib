"""upath._abc

Re-export of the `pathlib_abc` base classes `PathBase`, `PurePathBase`,
and `ParserBase`. This allows for type hinting of these classes more
easily via the stub file `upath/_abc.pyi`.
"""

from pathlib_abc import ParserBase as ParserBase
from pathlib_abc import PathBase as PathBase
from pathlib_abc import PurePathBase as PurePathBase
from pathlib_abc import UnsupportedOperation as UnsupportedOperation

__all__ = [
    "ParserBase",
    "PurePathBase",
    "PathBase",
    "UnsupportedOperation",
]
