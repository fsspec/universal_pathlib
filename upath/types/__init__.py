from __future__ import annotations

import enum
import os
import pathlib
import sys
from collections.abc import Iterator
from collections.abc import Sequence
from typing import IO
from typing import TYPE_CHECKING
from typing import Any
from typing import BinaryIO
from typing import Literal
from typing import Protocol
from typing import TextIO
from typing import Union
from typing import overload
from typing import runtime_checkable

from upath.types._abc import JoinablePath
from upath.types._abc import PathInfo
from upath.types._abc import PathParser
from upath.types._abc import ReadablePath
from upath.types._abc import WritablePath
from upath.types._abc import vfsopen

if TYPE_CHECKING:
    if sys.version_info > (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self

    if sys.version_info >= (3, 12):
        from typing import TypeAlias
    else:
        TypeAlias = Any

__all__ = [
    "JoinablePath",
    "ReadablePath",
    "WritablePath",
    "OpenablePath",
    "JoinablePathLike",
    "ReadablePathLike",
    "WritablePathLike",
    "CompatJoinablePath",
    "CompatReadablePath",
    "CompatWritablePath",
    "CompatOpenablePath",
    "PathInfo",
    "StatResultType",
    "PathParser",
    "UPathParser",
    "UNSET_DEFAULT",
]

JoinablePathLike: TypeAlias = Union[str, JoinablePath]
ReadablePathLike: TypeAlias = Union[str, ReadablePath]
WritablePathLike: TypeAlias = Union[str, WritablePath]


class _DefaultValue(enum.Enum):
    UNSET = enum.auto()


UNSET_DEFAULT: Any = _DefaultValue.UNSET


class OpenablePath(ReadablePath, WritablePath):
    """Helper class to annotate read/writable paths which have an .open() method."""

    __slots__ = ()

    @overload
    def open(
        self,
        mode: Literal["r", "w", "a"] = ...,
        buffering: int = ...,
        encoding: str = ...,
        errors: str = ...,
        newline: str = ...,
    ) -> TextIO: ...

    @overload
    def open(
        self,
        mode: Literal["rb", "wb", "ab"] = ...,
        buffering: int = ...,
        encoding: str = ...,
        errors: str = ...,
        newline: str = ...,
    ) -> BinaryIO: ...

    @overload
    def open(
        self,
        mode: str = ...,
        buffering: int = ...,
        encoding: str | None = ...,
        errors: str | None = ...,
        newline: str | None = ...,
    ) -> IO[Any]: ...

    def open(
        self,
        mode: str = "r",
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> IO[Any]:
        return vfsopen(self, mode, buffering, encoding, errors, newline)


if sys.version_info >= (3, 14):
    JoinablePath.register(pathlib.PurePath)
    ReadablePath.register(pathlib.Path)
    WritablePath.register(pathlib.Path)
    OpenablePath.register(pathlib.Path)


@runtime_checkable
class CompatJoinablePath(Protocol):
    # not available in Python 3.9.* pathlib:
    #  - `parser`
    #  - `with_segments`
    #  - `__vfspath__`
    #  - `full_match`
    __slots__ = ()

    @property
    def anchor(self) -> str: ...
    @property
    def name(self) -> str: ...
    @property
    def suffix(self) -> str: ...
    @property
    def suffixes(self) -> Sequence[str]: ...
    @property
    def stem(self) -> str: ...

    def with_name(self, name) -> Self: ...
    def with_stem(self, stem) -> Self: ...
    def with_suffix(self, suffix) -> Self: ...

    @property
    def parts(self) -> Sequence[str]: ...

    def joinpath(self, *pathsegments: str | Self) -> Self: ...
    def __truediv__(self, key: str | Self) -> Self: ...
    def __rtruediv__(self, key: str | Self) -> Self: ...

    @property
    def parent(self) -> Self: ...
    @property
    def parents(self) -> Sequence[Self]: ...


@runtime_checkable
class CompatReadablePath(CompatJoinablePath, Protocol):
    # not available in Python 3.9.* pathlib:
    #   - `info`
    #   - `__open_reader__`
    #   - `copy`
    #   - `copy_into`
    #   - `walk`
    __slots__ = ()

    def read_bytes(self) -> bytes: ...

    def read_text(
        self,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> str: ...

    def iterdir(self) -> Iterator[Self]: ...

    def glob(self, pattern: str, *, recurse_symlinks: bool = ...) -> Iterator[Self]: ...

    def readlink(self) -> Self: ...


@runtime_checkable
class CompatWritablePath(CompatJoinablePath, Protocol):
    # not available in Python 3.9.* pathlib:
    #   - `__open_writer__`
    #   - `_copy_from`
    __slots__ = ()

    def symlink_to(
        self, target: WritablePath, target_is_directory: bool = ...
    ) -> None: ...
    def mkdir(self) -> None: ...

    def write_bytes(self, data: bytes) -> int: ...

    def write_text(
        self,
        data: str,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> int: ...


@runtime_checkable
class CompatOpenablePath(CompatReadablePath, CompatWritablePath, Protocol):
    """A path that can be read from and written to."""

    __slots__ = ()

    @overload
    def open(
        self,
        mode: Literal["r", "w", "a"] = "r",
        buffering: int = ...,
        encoding: str = ...,
        errors: str = ...,
        newline: str = ...,
    ) -> TextIO: ...

    @overload
    def open(
        self,
        mode: Literal["rb", "wb", "ab"],
        buffering: int = ...,
        encoding: str = ...,
        errors: str = ...,
        newline: str = ...,
    ) -> BinaryIO: ...

    def open(
        self,
        mode: str = "r",
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> IO[Any]: ...


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
    @property
    def st_birthtime(self) -> float: ...
    @property
    def st_birthtime_ns(self) -> int: ...


@runtime_checkable
class UPathParser(PathParser, Protocol):
    """duck-type for upath.core.UPathParser"""

    def strip_protocol(self, path: JoinablePath | str) -> str: ...

    def join(
        self,
        path: JoinablePath | os.PathLike[str] | str,
        *paths: JoinablePath | os.PathLike[str] | str,
    ) -> str: ...

    def isabs(self, path: JoinablePath | os.PathLike[str] | str) -> bool: ...

    def splitdrive(
        self, path: JoinablePath | os.PathLike[str] | str
    ) -> tuple[str, str]: ...

    def splitroot(
        self, path: JoinablePath | os.PathLike[str] | str
    ) -> tuple[str, str, str]: ...
