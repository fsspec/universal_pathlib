"""upath._abc type stubs

Type stubs for the pathlib-abc classes we use in universal-pathlib.
"""

import sys
from typing import IO
from typing import Any
from typing import Callable
from typing import Generator
from typing import Sequence

if sys.version_info > (3, 11):
    from typing import Self
elif sys.version_info > (3, 8):

    from typing_extensions import Self
else:
    from typing_extensions import Self

from upath._stat import _StatResultType as StatResultType

class UnsupportedOperation(NotImplementedError): ...

class ParserBase:
    sep: str
    def join(self, path: str, *paths: str) -> str: ...
    def split(self, path: str) -> tuple[str, str]: ...
    def splitdrive(self, path: str) -> tuple[str, str]: ...
    def splitext(self, path: str) -> tuple[str, str]: ...
    def normcase(self, path: str) -> str: ...
    def isabs(self, path: str) -> bool: ...

class PurePathBase:
    _raw_path: str
    _resolving: bool

    @classmethod
    def _unsupported_msg(cls, attribute) -> str: ...
    def __init__(self, path, *paths) -> None: ...
    def with_segments(self, *pathsegments: str) -> Self: ...
    def __str__(self) -> str: ...
    def as_posix(self) -> str: ...
    drive: str
    root: str
    anchor: str
    name: str
    suffix: str
    suffixes: list[str]
    stem: str
    def with_name(self, name: str) -> Self: ...
    def with_stem(self, stem: str) -> Self: ...
    def with_suffix(self, suffix: str) -> Self: ...
    def relative_to(
        self, other: str | PurePathBase, *, walk_up: bool = False
    ) -> Self: ...
    def is_relative_to(self, other: str | PurePathBase) -> bool: ...
    parts: tuple[str, ...]
    def joinpath(self, *pathsegments: str) -> Self: ...
    def __truediv__(self, other: str) -> Self: ...
    def __rtruediv__(self, other: str) -> Self: ...
    _stack: tuple[str, list[str]]
    parent: Self
    parents: Sequence[Self]
    def is_absolute(self) -> bool: ...
    _pattern_str: str
    def match(
        self, path_pattern: str, *, case_sensitive: bool | None = None
    ) -> bool: ...
    def full_match(
        self, pattern: str, *, case_sensitive: bool | None = None
    ) -> bool: ...

class PathBase(PurePathBase):
    _max_symlinks: int

    def stat(self, *, follow_symlinks: bool = True) -> StatResultType: ...
    def lstat(self) -> StatResultType: ...
    def exists(self, *, follow_symlinks: bool = True) -> bool: ...
    def is_dir(self, *, follow_symlinks: bool = True) -> bool: ...
    def is_file(self, *, follow_symlinks: bool = True) -> bool: ...
    def is_mount(self) -> bool: ...
    def is_symlink(self) -> bool: ...
    def is_junction(self) -> bool: ...
    def is_block_device(self) -> bool: ...
    def is_char_device(self) -> bool: ...
    def is_fifo(self) -> bool: ...
    def is_socket(self) -> bool: ...
    def samefile(self, other_path: str | Self) -> bool: ...
    def open(
        self,
        mode: str = "r",
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> IO[Any]: ...
    def read_bytes(self) -> bytes: ...
    def read_text(
        self,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> str: ...
    def write_bytes(self, data: bytes) -> int: ...
    def write_text(
        self,
        data: str,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> int: ...
    def iterdir(self) -> Generator[Self, None, None]: ...
    def _glob_selector(
        self, parts: list[str], case_sensitive: bool | None, recurse_symlinks: bool
    ) -> Callable[[Self], Generator[Self, None, None]]: ...
    def glob(
        self,
        pattern: str,
        *,
        case_sensitive: bool | None = None,
        recurse_symlinks: bool = True,
    ) -> Generator[Self, None, None]: ...
    def rglob(
        self,
        pattern: str,
        *,
        case_sensitive: bool | None = None,
        recurse_symlinks: bool = True,
    ) -> Generator[Self, None, None]: ...
    def walk(
        self,
        top_down: bool = True,
        on_error: Callable[[Exception], None] | None = None,
        follow_symlinks: bool = False,
    ) -> Generator[tuple[Self, list[str], list[str]], None, None]: ...
    def absolute(self) -> Self: ...
    @classmethod
    def cwd(cls) -> Self: ...
    def expanduser(self) -> Self: ...
    @classmethod
    def home(cls) -> Self: ...
    def readlink(self) -> Self: ...
    def resolve(self, strict: bool = False) -> Self: ...
    def symlink_to(
        self, target: str | Self, target_is_directory: bool = False
    ) -> None: ...
    def hardlink_to(self, target: str | Self) -> None: ...
    def touch(self, mode: int = 0o666, exist_ok: bool = True) -> None: ...
    def mkdir(
        self, mode: int = 0o777, parents: bool = False, exist_ok: bool = False
    ) -> None: ...
    def rename(self, target: str | Self) -> Self: ...
    def replace(self, target: str | Self) -> Self: ...
    def chmod(self, mode: int, *, follow_symlinks: bool = True) -> None: ...
    def lchmod(self, mode: int) -> None: ...
    def unlink(self, missing_ok: bool = False) -> None: ...
    def rmdir(self) -> None: ...
    def owner(self, *, follow_symlinks: bool = True) -> str: ...
    def group(self, *, follow_symlinks: bool = True) -> str: ...
    @classmethod
    def from_uri(cls, uri: str) -> Self: ...
    def as_uri(self) -> str: ...
