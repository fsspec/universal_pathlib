from __future__ import annotations

import sys
from collections.abc import Iterator
from collections.abc import Mapping
from collections.abc import Sequence
from typing import IO
from typing import TYPE_CHECKING
from typing import Any
from typing import BinaryIO
from typing import Callable
from typing import Literal
from typing import TextIO
from typing import overload
from urllib.parse import SplitResult

from fsspec import AbstractFileSystem

from upath._stat import UPathStatResult
from upath.core import UPath
from upath.types import UNSET_DEFAULT
from upath.types import JoinablePathLike
from upath.types import PathInfo
from upath.types import ReadablePath
from upath.types import ReadablePathLike
from upath.types import UPathParser
from upath.types import WritablePathLike

if TYPE_CHECKING:
    if sys.version_info > (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self

__all__ = [
    "ProxyUPath",
]


class ProxyUPath:
    """ProxyUPath base class

    ProxyUPath should be used when you want to extend the UPath class
    interface with additional methods, but still want to support
    all supported upath implementations.

    """

    __slots__ = ("__wrapped__",)

    # TODO: think about if and how to handle these
    #  _transform_init_args
    #  _parse_storage_options
    #  _fs_factory
    #  _protocol_dispatch

    def __init__(
        self,
        *args: JoinablePathLike,
        protocol: str | None = None,
        **storage_options: Any,
    ) -> None:
        self.__wrapped__ = UPath(*args, protocol=protocol, **storage_options)

    @classmethod
    def _from_upath(cls, upath: UPath, /) -> Self:
        if isinstance(upath, cls):
            return upath  # type: ignore[unreachable]
        else:
            obj = object.__new__(cls)
            obj.__wrapped__ = upath
            return obj

    @property
    def parser(self) -> UPathParser:
        return self.__wrapped__.parser

    def with_segments(self) -> Self:
        return self._from_upath(self.__wrapped__.with_segments())

    def __str__(self) -> str:
        return self.__wrapped__.__str__()

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}"
            f"({self.__wrapped__.path!r}, protocol={self.protocol!r})"
        )

    @property
    def parts(self) -> Sequence[str]:
        return self.__wrapped__.parts

    def with_name(self, name: str) -> Self:
        return self._from_upath(self.__wrapped__.with_name(name))

    @property
    def info(self) -> PathInfo:
        return self.__wrapped__.info

    def iterdir(self) -> Iterator[Self]:
        for pth in self.__wrapped__.iterdir():
            yield self._from_upath(pth)

    def __open_rb__(self, buffering: int = -1) -> BinaryIO:
        return self.__wrapped__.__open_rb__(buffering)

    def readlink(self) -> Self:
        return self._from_upath(self.__wrapped__.readlink())

    def symlink_to(
        self,
        target: ReadablePathLike,
        target_is_directory: bool = False,
    ) -> None:
        self.__wrapped__.symlink_to(target, target_is_directory=target_is_directory)

    def mkdir(
        self,
        mode: int = 0o777,
        parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
        self.__wrapped__.mkdir(mode=mode, parents=parents, exist_ok=exist_ok)

    def __open_wb__(self, buffering: int = -1) -> BinaryIO:
        return self.__wrapped__.__open_wb__(buffering)

    @overload
    def open(
        self,
        mode: Literal["r", "w", "a"] = "r",
        buffering: int = ...,
        encoding: str = ...,
        errors: str = ...,
        newline: str = ...,
        **fsspec_kwargs: Any,
    ) -> TextIO: ...

    @overload
    def open(
        self,
        mode: Literal["rb", "wb", "ab"],
        buffering: int = ...,
        encoding: str = ...,
        errors: str = ...,
        newline: str = ...,
        **fsspec_kwargs: Any,
    ) -> BinaryIO: ...

    @overload
    def open(
        self,
        mode: str,
        *args: Any,
        **fsspec_kwargs: Any,
    ) -> IO[Any]: ...

    def open(
        self,
        mode: str = "r",
        buffering: int = UNSET_DEFAULT,
        encoding: str | None = UNSET_DEFAULT,
        errors: str | None = UNSET_DEFAULT,
        newline: str | None = UNSET_DEFAULT,
        **fsspec_kwargs: Any,
    ) -> IO[Any]:
        return self.__wrapped__.open(
            mode,
            buffering,
            encoding,
            errors,
            newline,
            **fsspec_kwargs,
        )

    def stat(
        self,
        *,
        follow_symlinks=True,
    ) -> UPathStatResult:
        return self.__wrapped__.stat(follow_symlinks=follow_symlinks)

    def lstat(self) -> UPathStatResult:
        return self.__wrapped__.stat(follow_symlinks=False)

    def chmod(self, mode: int, *, follow_symlinks: bool = True) -> None:
        self.__wrapped__.chmod(mode=mode, follow_symlinks=follow_symlinks)

    def exists(self, *, follow_symlinks=True) -> bool:
        return self.__wrapped__.exists(follow_symlinks=follow_symlinks)

    def is_dir(self) -> bool:
        return self.__wrapped__.is_dir()

    def is_file(self) -> bool:
        return self.__wrapped__.is_file()

    def is_mount(self) -> bool:
        return self.__wrapped__.is_mount()

    def is_symlink(self) -> bool:
        return self.__wrapped__.is_symlink()

    def is_junction(self) -> bool:
        return self.__wrapped__.is_junction()

    def is_block_device(self) -> bool:
        return self.__wrapped__.is_block_device()

    def is_char_device(self) -> bool:
        return self.__wrapped__.is_char_device()

    def is_fifo(self) -> bool:
        return self.__wrapped__.is_fifo()

    def is_socket(self) -> bool:
        return self.__wrapped__.is_socket()

    def is_reserved(self) -> bool:
        return self.__wrapped__.is_reserved()

    def expanduser(self) -> Self:
        return self._from_upath(self.__wrapped__.expanduser())

    def glob(
        self,
        pattern: str,
        *,
        case_sensitive: bool = UNSET_DEFAULT,
        recurse_symlinks: bool = UNSET_DEFAULT,
    ) -> Iterator[Self]:
        for p in self.__wrapped__.glob(
            pattern, case_sensitive=case_sensitive, recurse_symlinks=recurse_symlinks
        ):
            yield self._from_upath(p)

    def rglob(
        self,
        pattern: str,
        *,
        case_sensitive: bool = UNSET_DEFAULT,
        recurse_symlinks: bool = UNSET_DEFAULT,
    ) -> Iterator[Self]:
        for p in self.__wrapped__.rglob(
            pattern, case_sensitive=case_sensitive, recurse_symlinks=recurse_symlinks
        ):
            yield self._from_upath(p)

    def owner(self) -> str:
        return self.__wrapped__.owner()

    def group(self) -> str:
        return self.__wrapped__.group()

    def absolute(self) -> Self:
        return self._from_upath(self.__wrapped__.absolute())

    def is_absolute(self) -> bool:
        return self.__wrapped__.is_absolute()

    def __eq__(self, other: object) -> bool:
        return self.__wrapped__.__eq__(other)

    def __hash__(self) -> int:
        return self.__wrapped__.__hash__()

    def __lt__(self, other: object) -> bool:
        return self.__wrapped__.__lt__(other)

    def __le__(self, other: object) -> bool:
        return self.__wrapped__.__le__(other)

    def __gt__(self, other: object) -> bool:
        return self.__wrapped__.__gt__(other)

    def __ge__(self, other: object) -> bool:
        return self.__wrapped__.__ge__(other)

    def resolve(self, strict: bool = False) -> Self:
        return self._from_upath(self.__wrapped__.resolve(strict=strict))

    def touch(self, mode=0o666, exist_ok=True) -> None:
        self.__wrapped__.touch(mode=mode, exist_ok=exist_ok)

    def lchmod(self, mode: int) -> None:
        self.__wrapped__.lchmod(mode=mode)

    def unlink(self, missing_ok: bool = False) -> None:
        self.__wrapped__.unlink(missing_ok=missing_ok)

    def rmdir(self, recursive: bool = True) -> None:  # fixme: non-standard
        self.__wrapped__.rmdir(recursive=recursive)

    def rename(
        self,
        target: WritablePathLike,
        *,  # note: non-standard compared to pathlib
        recursive: bool = UNSET_DEFAULT,
        maxdepth: int | None = UNSET_DEFAULT,
        **kwargs: Any,
    ) -> Self:
        return self._from_upath(
            self.__wrapped__.rename(
                target, recursive=recursive, maxdepth=maxdepth, **kwargs
            )
        )

    def replace(self, target: WritablePathLike) -> Self:
        return self._from_upath(self.__wrapped__.replace(target))

    @property
    def drive(self) -> str:
        return self.__wrapped__.drive

    @property
    def root(self) -> str:
        return self.__wrapped__.root

    def __reduce__(self):
        return type(self)._from_upath, (self.__wrapped__,)

    def as_uri(self) -> str:
        return self.__wrapped__.as_uri()

    def as_posix(self) -> str:
        return self.__wrapped__.as_posix()

    def samefile(self, other_path) -> bool:
        return self.__wrapped__.samefile(other_path)

    @classmethod
    def cwd(cls) -> Self:
        raise NotImplementedError

    @classmethod
    def home(cls) -> Self:
        raise NotImplementedError

    def relative_to(  # type: ignore[override]
        self,
        other,
        /,
        *_deprecated,
        walk_up=False,
    ) -> Self:
        return self._from_upath(
            self.__wrapped__.relative_to(other, *_deprecated, walk_up=walk_up)
        )

    def is_relative_to(self, other, /, *_deprecated) -> bool:  # type: ignore[override]
        return self.__wrapped__.is_relative_to(other, *_deprecated)

    def hardlink_to(self, target: ReadablePathLike) -> None:
        return self.__wrapped__.hardlink_to(target)

    def match(self, pattern: str) -> bool:
        return self.__wrapped__.match(pattern)

    @property
    def protocol(self) -> str:
        return self.__wrapped__.protocol

    @property
    def storage_options(self) -> Mapping[str, Any]:
        return self.__wrapped__.storage_options

    @property
    def fs(self) -> AbstractFileSystem:
        return self.__wrapped__.fs

    @property
    def path(self) -> str:
        return self.__wrapped__.path

    def joinuri(self, uri: JoinablePathLike) -> Self:
        return self._from_upath(self.__wrapped__.joinuri(uri))

    @property
    def _url(self) -> SplitResult:
        return self.__wrapped__._url

    def read_bytes(self) -> bytes:
        return self.__wrapped__.read_bytes()

    def read_text(
        self,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> str:
        return self.__wrapped__.read_text(
            encoding=encoding, errors=errors, newline=newline
        )

    def walk(
        self,
        top_down: bool = True,
        on_error: Callable[[Exception], Any] | None = None,
        follow_symlinks: bool = False,
    ) -> Iterator[tuple[Self, list[str], list[str]]]:
        for pth, dirnames, filenames in self.__wrapped__.walk(
            top_down=top_down, on_error=on_error, follow_symlinks=follow_symlinks
        ):
            yield self._from_upath(pth), dirnames, filenames

    def copy(self, target: UPath, **kwargs: Any) -> Self:
        return self._from_upath(self.__wrapped__.copy(target, **kwargs))

    def copy_into(self, target_dir: UPath, **kwargs: Any) -> Self:
        return self._from_upath(self.__wrapped__.copy_into(target_dir, **kwargs))

    def write_bytes(self, data: bytes) -> int:
        return self.__wrapped__.write_bytes(data)

    def write_text(
        self,
        data: str,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> int:
        return self.__wrapped__.write_text(
            data, encoding=encoding, errors=errors, newline=newline
        )

    def _copy_from(self, source: ReadablePath, follow_symlinks: bool = True) -> None:
        self.__wrapped__._copy_from(source, follow_symlinks=follow_symlinks)

    @property
    def anchor(self) -> str:
        return self.__wrapped__.anchor

    @property
    def name(self) -> str:
        return self.__wrapped__.name

    @property
    def suffix(self) -> str:
        return self.__wrapped__.suffix

    @property
    def suffixes(self) -> Sequence[str]:
        return self.__wrapped__.suffixes

    @property
    def stem(self) -> str:
        return self.__wrapped__.stem

    def with_stem(self, stem: str) -> Self:
        return self._from_upath(self.__wrapped__.with_stem(stem))

    def with_suffix(self, suffix: str) -> Self:
        return self._from_upath(self.__wrapped__.with_suffix(suffix))

    def joinpath(self, *pathsegments: str) -> Self:
        return self._from_upath(self.__wrapped__.joinpath(*pathsegments))

    def __truediv__(self, other: str | Self) -> Self:
        return self._from_upath(
            self.__wrapped__.__truediv__(other)  # type: ignore[operator]
        )

    def __rtruediv__(self, other: str | Self) -> Self:
        return self._from_upath(
            self.__wrapped__.__rtruediv__(other)  # type: ignore[operator]
        )

    @property
    def parent(self) -> Self:
        return self._from_upath(self.__wrapped__.parent)

    @property
    def parents(self) -> Sequence[Self]:
        return tuple(self._from_upath(p) for p in self.__wrapped__.parents)

    def full_match(self, pattern: str) -> bool:
        return self.__wrapped__.full_match(pattern)


UPath.register(ProxyUPath)
