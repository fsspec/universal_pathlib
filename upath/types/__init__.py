from __future__ import annotations

import enum
import sys
from os import PathLike
from typing import TYPE_CHECKING
from typing import Any
from typing import Protocol
from typing import Union
from typing import runtime_checkable

from upath.types._abc import JoinablePath
from upath.types._abc import PathInfo
from upath.types._abc import PathParser
from upath.types._abc import ReadablePath
from upath.types._abc import WritablePath

if TYPE_CHECKING:

    if sys.version_info >= (3, 12):
        from typing import TypeAlias
    else:
        from typing_extensions import TypeAlias

__all__ = [
    "JoinablePath",
    "ReadablePath",
    "WritablePath",
    "JoinablePathLike",
    "ReadablePathLike",
    "WritablePathLike",
    "SupportsPathLike",
    "PathInfo",
    "StatResultType",
    "PathParser",
    "UPathParser",
    "UNSET_DEFAULT",
]


class VFSPathLike(Protocol):
    def __vfspath__(self) -> str: ...


SupportsPathLike: TypeAlias = Union[VFSPathLike, PathLike[str]]
JoinablePathLike: TypeAlias = Union[JoinablePath, SupportsPathLike, str]
ReadablePathLike: TypeAlias = Union[ReadablePath, SupportsPathLike, str]
WritablePathLike: TypeAlias = Union[WritablePath, SupportsPathLike, str]


class _DefaultValue(enum.Enum):
    UNSET = enum.auto()


UNSET_DEFAULT: Any = _DefaultValue.UNSET

# We can't assume this, because pathlib_abc==0.5.1 is ahead of stdlib 3.14
# if sys.version_info >= (3, 14):
#     JoinablePath.register(pathlib.PurePath)
#     ReadablePath.register(pathlib.Path)
#     WritablePath.register(pathlib.Path)


@runtime_checkable
class StatResultType(Protocol):
    """duck-type for os.stat_result"""

    @property
    def st_mode(self) -> int: ...
    @property
    def st_ino(self) -> int: ...
    @property
    def st_dev(self) -> int: ...
    @property
    def st_nlink(self) -> int: ...
    @property
    def st_uid(self) -> int: ...
    @property
    def st_gid(self) -> int: ...
    @property
    def st_size(self) -> int: ...
    @property
    def st_atime(self) -> float: ...
    @property
    def st_mtime(self) -> float: ...
    @property
    def st_ctime(self) -> float: ...
    @property
    def st_atime_ns(self) -> int: ...
    @property
    def st_mtime_ns(self) -> int: ...
    @property
    def st_ctime_ns(self) -> int: ...

    # st_birthtime is available on Windows (3.12+), FreeBSD, and macOS
    # On Linux it's currently unavailable
    # see: https://discuss.python.org/t/st-birthtime-not-available/104350/2
    if (sys.platform == "win32" and sys.version_info >= (3, 12)) or (
        sys.platform == "darwin" or sys.platform.startswith("freebsd")
    ):

        @property
        def st_birthtime(self) -> float: ...


@runtime_checkable
class UPathParser(PathParser, Protocol):
    """duck-type for upath.core.UPathParser"""

    def split(self, path: JoinablePathLike) -> tuple[str, str]: ...
    def splitext(self, path: JoinablePathLike) -> tuple[str, str]: ...
    def normcase(self, path: JoinablePathLike) -> str: ...

    def strip_protocol(self, path: JoinablePathLike) -> str: ...

    def join(
        self,
        path: JoinablePathLike,
        *paths: JoinablePathLike,
    ) -> str: ...

    def isabs(self, path: JoinablePathLike) -> bool: ...

    def splitdrive(self, path: JoinablePathLike) -> tuple[str, str]: ...

    def splitroot(self, path: JoinablePathLike) -> tuple[str, str, str]: ...
