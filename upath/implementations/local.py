from __future__ import annotations

import os
import pathlib
import shutil
import sys
import warnings
from collections.abc import Iterator
from collections.abc import Sequence
from typing import TYPE_CHECKING
from typing import Any
from typing import Callable
from typing import Literal
from typing import overload
from urllib.parse import SplitResult

from fsspec import AbstractFileSystem

from upath._chain import DEFAULT_CHAIN_PARSER
from upath._chain import Chain
from upath._chain import ChainSegment
from upath._chain import FSSpecChainParser
from upath._protocol import compatible_protocol
from upath.core import UnsupportedOperation
from upath.core import UPath
from upath.core import _UPathMixin
from upath.types import UNSET_DEFAULT
from upath.types import JoinablePathLike
from upath.types import PathInfo
from upath.types import ReadablePath
from upath.types import ReadablePathLike
from upath.types import StatResultType
from upath.types import SupportsPathLike
from upath.types import WritablePath
from upath.types import WritablePathLike

if TYPE_CHECKING:
    from typing import IO
    from typing import BinaryIO
    from typing import TextIO
    from typing import TypeVar

    if sys.version_info >= (3, 11):
        from typing import Self
        from typing import Unpack
    else:
        from typing_extensions import Self
        from typing_extensions import Unpack

    from upath.types.storage_options import FileStorageOptions

    _WT = TypeVar("_WT", bound="WritablePath")

__all__ = [
    "LocalPath",
    "PosixUPath",
    "WindowsUPath",
    "FilePath",
]


_LISTDIR_WORKS_ON_FILES: bool | None = None


def _check_listdir_works_on_files() -> bool:
    global _LISTDIR_WORKS_ON_FILES
    from fsspec.implementations.local import LocalFileSystem

    fs = LocalFileSystem()
    try:
        fs.ls(__file__)
    except NotADirectoryError:
        _LISTDIR_WORKS_ON_FILES = w = False
    else:
        _LISTDIR_WORKS_ON_FILES = w = True
    return w


def _warn_protocol_storage_options(
    cls: type,
    protocol: str | None,
    storage_options: dict[str, Any],
) -> None:
    if protocol in {"", None} and not storage_options:
        return
    warnings.warn(
        f"{cls.__name__} on python <= (3, 11) ignores protocol and storage_options",
        UserWarning,
        stacklevel=3,
    )


class _LocalPathInfo(PathInfo):
    """Backported PathInfo implementation for LocalPath.
    todo: currently not handling symlinks correctly.
    """

    def __init__(self, path: LocalPath) -> None:
        self._path = path.path

    def exists(self, *, follow_symlinks: bool = True) -> bool:
        return os.path.exists(self._path)

    def is_dir(self, *, follow_symlinks: bool = True) -> bool:
        return os.path.isdir(self._path)

    def is_file(self, *, follow_symlinks: bool = True) -> bool:
        return os.path.isfile(self._path)

    def is_symlink(self) -> bool:
        return os.path.islink(self._path)


class LocalPath(_UPathMixin, pathlib.Path):
    __slots__ = (
        "_chain",
        "_chain_parser",
        "_fs_cached",
        "_relative_base",
    )
    if TYPE_CHECKING:
        _chain: Chain
        _chain_parser: FSSpecChainParser
        _fs_cached: AbstractFileSystem
        _relative_base: str | None

    parser = os.path  # type: ignore[misc,assignment]

    @property
    def _raw_urlpaths(self) -> Sequence[JoinablePathLike]:
        return self.parts

    @_raw_urlpaths.setter
    def _raw_urlpaths(self, value: Sequence[JoinablePathLike]) -> None:
        pass

    if sys.version_info >= (3, 14):

        def rename(
            self,
            target: WritablePathLike,
        ) -> Self:
            t = super().rename(target)  # type: ignore[arg-type]
            if not isinstance(target, type(self)):
                return self.with_segments(t)
            else:
                return t

    if sys.version_info >= (3, 12):

        def __init__(
            self,
            *args,
            protocol: str | None = None,
            chain_parser: FSSpecChainParser = DEFAULT_CHAIN_PARSER,
            **storage_options: Any,
        ) -> None:
            super(_UPathMixin, self).__init__(*args)
            self._chain = Chain(ChainSegment(str(self), "", storage_options))
            self._chain_parser = chain_parser

    elif sys.version_info >= (3, 10):

        def __init__(
            self,
            *args,
            protocol: str | None = None,
            chain_parser: FSSpecChainParser = DEFAULT_CHAIN_PARSER,
            **storage_options: Any,
        ) -> None:
            # super(_UPathMixin, self).__init__(*args)
            _warn_protocol_storage_options(type(self), protocol, storage_options)
            self._drv, self._root, self._parts = self._parse_args(args)  # type: ignore[attr-defined] # noqa: E501
            self._chain = Chain(ChainSegment(str(self), "", {}))
            self._chain_parser = chain_parser

        @classmethod
        def _from_parts(cls, args):
            obj = super()._from_parts(args)
            obj._chain = Chain(ChainSegment(str(obj), "", {}))
            return obj

        @classmethod
        def _from_parsed_parts(cls, drv, root, parts):
            obj = super()._from_parsed_parts(drv, root, parts)
            obj._chain = Chain(ChainSegment(str(obj), "", {}))
            return obj

    else:

        def __init__(
            self,
            *args,
            protocol: str | None = None,
            chain_parser: FSSpecChainParser = DEFAULT_CHAIN_PARSER,
            **storage_options: Any,
        ) -> None:
            _warn_protocol_storage_options(type(self), protocol, storage_options)
            self._drv, self._root, self._parts = self._parse_args(args)  # type: ignore[attr-defined] # noqa: E501
            self._init()
            self._chain_parser = chain_parser

        def _init(self, **kwargs: Any) -> None:
            super()._init(**kwargs)  # type: ignore[misc]
            self._chain = Chain(ChainSegment(str(self), "", {}))

    def __vfspath__(self) -> str:
        return self.__fspath__()

    def __open_reader__(self) -> BinaryIO:
        return self.open("rb")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, UPath):
            return NotImplemented
        eq_path = super().__eq__(other)
        if eq_path is NotImplemented:
            return NotImplemented
        return (
            eq_path
            and self.protocol == other.protocol
            and self.storage_options == other.storage_options
        )

    def __ne__(self, other: object) -> bool:
        if not isinstance(other, UPath):
            return NotImplemented
        ne_path = super().__ne__(other)
        if ne_path is NotImplemented:
            return NotImplemented
        return (
            ne_path
            or self.protocol != other.protocol
            or self.storage_options != other.storage_options
        )

    def __hash__(self) -> int:
        return super().__hash__()

    if sys.version_info >= (3, 14):

        def __open_rb__(self, buffering: int = UNSET_DEFAULT) -> BinaryIO:
            return self.open("rb", buffering=buffering)

    def __open_writer__(self, mode: Literal["a", "w", "x"]) -> BinaryIO:
        if mode == "w":
            return self.open(mode="wb")
        elif mode == "a":
            return self.open(mode="ab")
        elif mode == "x":
            return self.open(mode="xb")
        else:
            raise ValueError(f"invalid mode: {mode}")

    def with_segments(self, *pathsegments: str | os.PathLike[str]) -> Self:
        return type(self)(
            *pathsegments,
            protocol=self._protocol,
            **self._storage_options,
        )

    @property
    def path(self) -> str:
        return self.as_posix()

    @property
    def _url(self) -> SplitResult:
        return SplitResult._make((self.protocol, "", self.path, "", ""))

    def joinpath(self, *other) -> Self:
        if not compatible_protocol("", *other):
            raise ValueError("can't combine incompatible UPath protocols")
        return super().joinpath(
            *(
                str(o) if isinstance(o, UPath) and not o.is_absolute() else o
                for o in other
            )
        )

    def __truediv__(self, other) -> Self:
        if not compatible_protocol("", other):
            raise ValueError("can't combine incompatible UPath protocols")
        return super().__truediv__(
            str(other)
            if isinstance(other, UPath) and not other.is_absolute()
            else other
        )

    def __rtruediv__(self, other) -> Self:
        if not compatible_protocol("", other):
            raise ValueError("can't combine incompatible UPath protocols")
        return super().__rtruediv__(
            str(other)
            if isinstance(other, UPath) and not other.is_absolute()
            else other
        )

    @overload  # type: ignore[override]
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
        mode: Literal["rb", "wb", "ab", "xb"],
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
        buffering: int = ...,
        encoding: str | None = ...,
        errors: str | None = ...,
        newline: str | None = ...,
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
        if not fsspec_kwargs:
            kwargs: dict[str, str | int | None] = {}
            if buffering is not UNSET_DEFAULT:
                kwargs["buffering"] = buffering
            if encoding is not UNSET_DEFAULT:
                kwargs["encoding"] = encoding
            if errors is not UNSET_DEFAULT:
                kwargs["errors"] = errors
            if newline is not UNSET_DEFAULT:
                kwargs["newline"] = newline
            return super().open(mode, **kwargs)  # type: ignore  # noqa: E501
        return UPath.open.__get__(self)(
            mode,
            buffering=buffering,
            encoding=encoding,
            errors=errors,
            newline=newline,
            **fsspec_kwargs,
        )

    def rmdir(self, recursive: bool = UNSET_DEFAULT) -> None:
        if recursive is UNSET_DEFAULT or not recursive:
            return super().rmdir()
        else:
            shutil.rmtree(self)

    if sys.version_info < (3, 14):  # noqa: C901

        @overload
        def copy(self, target: _WT, **kwargs: Any) -> _WT: ...

        @overload
        def copy(self, target: SupportsPathLike | str, **kwargs: Any) -> Self: ...

        def copy(
            self, target: _WT | SupportsPathLike | str, **kwargs: Any
        ) -> _WT | Self:
            # hacky workaround for missing pathlib.Path.copy in python < 3.14
            # todo: revisit
            _copy: Any = ReadablePath.copy.__get__(self)
            if not isinstance(target, UPath):
                return _copy(self.with_segments(str(target)), **kwargs)
            else:
                return _copy(target, **kwargs)

        @overload
        def copy_into(self, target_dir: _WT, **kwargs: Any) -> _WT: ...

        @overload
        def copy_into(
            self, target_dir: SupportsPathLike | str, **kwargs: Any
        ) -> Self: ...

        def copy_into(
            self,
            target_dir: _WT | SupportsPathLike | str,
            **kwargs: Any,
        ) -> _WT | Self:
            # hacky workaround for missing pathlib.Path.copy_into in python < 3.14
            # todo: revisit
            _copy_into: Any = ReadablePath.copy_into.__get__(self)
            if not isinstance(target_dir, UPath):
                return _copy_into(self.with_segments(str(target_dir)), **kwargs)
            else:
                return _copy_into(target_dir, **kwargs)

        @overload
        def move(self, target: _WT, **kwargs: Any) -> _WT: ...

        @overload
        def move(self, target: SupportsPathLike | str, **kwargs: Any) -> Self: ...

        def move(
            self, target: _WT | SupportsPathLike | str, **kwargs: Any
        ) -> _WT | Self:
            target = self.copy(target, **kwargs)
            self.fs.rm(self.path, recursive=self.is_dir())
            return target

        @overload
        def move_into(self, target_dir: _WT, **kwargs: Any) -> _WT: ...

        @overload
        def move_into(
            self, target_dir: SupportsPathLike | str, **kwargs: Any
        ) -> Self: ...

        def move_into(
            self, target_dir: _WT | SupportsPathLike | str, **kwargs: Any
        ) -> _WT | Self:
            name = self.name
            if not name:
                raise ValueError(f"{self!r} has an empty name")
            elif hasattr(target_dir, "with_segments"):
                target = target_dir.with_segments(str(target_dir), name)  # type: ignore
            else:
                target = self.with_segments(str(target_dir), name)
            return self.move(target)

        @property
        def info(self) -> PathInfo:
            return _LocalPathInfo(self)

    if sys.version_info < (3, 13):  # noqa: C901

        def full_match(
            self,
            pattern: str | os.PathLike[str],
            *,
            case_sensitive: bool | None = None,
        ) -> bool:
            # hacky workaround for missing pathlib.Path.full_match in python < 3.13
            # todo: revisit
            return self.match(
                pattern,  # type: ignore[arg-type]
                case_sensitive=case_sensitive,
            )

        @classmethod
        def from_uri(cls, uri: str, **storage_options: Any) -> Self:
            return UPath(uri, **storage_options)  # type: ignore[return-value]

        def is_dir(self, *, follow_symlinks: bool = True) -> bool:
            if not follow_symlinks:
                warnings.warn(
                    f"{type(self).__name__}.is_dir(): follow_symlinks=False"
                    " is currently ignored.",
                    UserWarning,
                    stacklevel=2,
                )
            return super().is_dir()

        def is_file(self, *, follow_symlinks: bool = True) -> bool:
            if not follow_symlinks:
                warnings.warn(
                    f"{type(self).__name__}.is_file(): follow_symlinks=False"
                    " is currently ignored.",
                    UserWarning,
                    stacklevel=2,
                )
            return super().is_file()

        def read_text(
            self,
            encoding: str | None = None,
            errors: str | None = None,
            newline: str | None = None,
        ) -> str:
            if newline is not None:
                warnings.warn(
                    f"{type(self).__name__}.read_text(): newline"
                    " is currently ignored.",
                    UserWarning,
                    stacklevel=2,
                )
            return super().read_text(
                encoding=encoding,
                errors=errors,
            )

        def glob(  # type: ignore[override]
            self,
            pattern: str | os.PathLike,
            *,
            case_sensitive: bool | None = None,
            recurse_symlinks: bool = False,
        ) -> Iterator[Self]:
            if isinstance(pattern, str):
                pattern_str = pattern
            else:
                pattern_str = os.fspath(pattern)
            kw: dict[str, Any] = {}
            if case_sensitive is not None:
                if sys.version_info < (3, 12):
                    warnings.warn(
                        f"{type(self).__name__}.glob(): case_sensitive"
                        " is currently ignored.",
                        UserWarning,
                        stacklevel=2,
                    )
                else:
                    kw["case_sensitive"] = case_sensitive
            if recurse_symlinks:
                warnings.warn(
                    f"{type(self).__name__}.glob(): recurse_symlinks=True"
                    " is currently ignored.",
                    UserWarning,
                    stacklevel=2,
                )
            return super().glob(pattern_str, **kw)

        def rglob(  # type: ignore[override]
            self,
            pattern: str | os.PathLike,
            *,
            case_sensitive: bool | None = None,
            recurse_symlinks: bool = False,
        ) -> Iterator[Self]:
            if isinstance(pattern, str):
                pattern_str = pattern
            else:
                pattern_str = os.fspath(pattern)
            kw: dict[str, Any] = {}
            if case_sensitive is not None:
                if sys.version_info < (3, 12):
                    warnings.warn(
                        f"{type(self).__name__}.rglob(): case_sensitive"
                        " is currently ignored.",
                        UserWarning,
                        stacklevel=2,
                    )
                else:
                    kw["case_sensitive"] = case_sensitive
            if recurse_symlinks:
                warnings.warn(
                    f"{type(self).__name__}.rglob(): recurse_symlinks=True"
                    " is currently ignored.",
                    UserWarning,
                    stacklevel=2,
                )
            return super().rglob(pattern_str, **kw)

        def owner(self, *, follow_symlinks: bool = True) -> str:
            if not follow_symlinks:
                warnings.warn(
                    f"{type(self).__name__}.owner() follow_symlinks=False"
                    " is currently ignored.",
                    UserWarning,
                    stacklevel=2,
                )
            return super().owner()

        def group(self, *, follow_symlinks: bool = True) -> str:
            if not follow_symlinks:
                warnings.warn(
                    f"{type(self).__name__}.group() follow_symlinks=False"
                    " is currently ignored.",
                    UserWarning,
                    stacklevel=2,
                )
            return super().group()

    if sys.version_info < (3, 12):

        def is_junction(self) -> bool:
            return False

        def walk(
            self,
            top_down: bool = True,
            on_error: Callable[[Exception], Any] | None = None,
            follow_symlinks: bool = False,
        ) -> Iterator[tuple[Self, list[str], list[str]]]:
            _walk = ReadablePath.walk.__get__(self)
            return _walk(top_down, on_error, follow_symlinks)

        def match(
            self,
            path_pattern: str | os.PathLike[str],
            *,
            case_sensitive: bool | None = None,
        ) -> bool:
            if isinstance(path_pattern, str):
                pattern_str = path_pattern
            else:
                pattern_str = os.fspath(path_pattern)
            if case_sensitive is not None:
                warnings.warn(
                    f"{type(self).__name__}.match(): case_sensitive"
                    " is currently ignored.",
                    UserWarning,
                    stacklevel=2,
                )
            return super().match(pattern_str)

        def exists(self, *, follow_symlinks: bool = True) -> bool:
            if not follow_symlinks:
                warnings.warn(
                    f"{type(self).__name__}.exists(): follow_symlinks=False"
                    " is currently ignored.",
                    UserWarning,
                    stacklevel=2,
                )
            return super().exists()

        def relative_to(  # type: ignore[override]
            self,
            other: str | os.PathLike[str],
            /,
            *_deprecated: str | os.PathLike[str],
            walk_up: bool = False,
        ) -> Self:
            if walk_up:
                warnings.warn(
                    f"{type(self).__name__}.relative_to() walk_up=True"
                    " is currently ignored.",
                    UserWarning,
                    stacklevel=2,
                )
            return super().relative_to(other, *_deprecated)

    if sys.version_info < (3, 10):

        def hardlink_to(self, target: ReadablePathLike) -> None:
            try:
                os.link(target, self)  # type: ignore[arg-type]
            except AttributeError:
                raise UnsupportedOperation("hardlink operation not supported")

        # let's skip this one as backporting it breaks one pathlib test
        # @property
        # def parents(self) -> Sequence[Self]:
        #     return list(super().parents)

        def stat(  # type: ignore[override]
            self,
            *,
            follow_symlinks: bool = True,
        ) -> StatResultType:
            if not follow_symlinks:
                warnings.warn(
                    f"{type(self).__name__}.stat() follow_symlinks=False"
                    " is currently ignored.",
                    UserWarning,
                    stacklevel=2,
                )
            return super().stat()  # type: ignore[return-value]

        def write_text(
            self,
            data: str,
            encoding: str | None = None,
            errors: str | None = None,
            newline: str | None = None,
        ) -> int:
            if newline is not None:
                warnings.warn(
                    f"{type(self).__name__}.write_text() newline"
                    " is currently ignored.",
                    UserWarning,
                    stacklevel=2,
                )
            return super().write_text(
                data,
                encoding=encoding,
                errors=errors,
            )

        def chmod(
            self,
            mode: int,
            *,
            follow_symlinks: bool = True,
        ) -> None:
            if not follow_symlinks:
                warnings.warn(
                    f"{type(self).__name__}.chmod() follow_symlinks=False"
                    " is currently ignored.",
                    UserWarning,
                    stacklevel=2,
                )
            return super().chmod(mode)

    if not hasattr(pathlib.Path, "_copy_from"):

        def _copy_from(
            self,
            source: ReadablePath | LocalPath,
            follow_symlinks: bool = True,
            preserve_metadata: bool = False,
        ) -> None:
            _copy_from: Any = WritablePath._copy_from.__get__(self)
            _copy_from(source, follow_symlinks=follow_symlinks)


UPath.register(LocalPath)


# Mypy will ignore the ABC.register call above, so we need to force it to
# think PosixUPath and WindowsUPath are subclasses of UPath.
# This is really not a good pattern, but it's the best we can do without
# either introducing a duck-type protocol for UPath or come up with a
# better solution for the UPath versions of the pathlib.Path subclasses.

if TYPE_CHECKING:

    class WindowsUPath(LocalPath, pathlib.WindowsPath, UPath):  # type: ignore[misc]
        __slots__ = ()

    class PosixUPath(LocalPath, pathlib.PosixPath, UPath):  # type: ignore[misc]
        __slots__ = ()

else:

    class WindowsUPath(LocalPath, pathlib.WindowsPath):
        __slots__ = ()

        if os.name != "nt":

            def __new__(
                cls,
                *args,
                protocol: str | None = None,
                chain_parser: FSSpecChainParser = DEFAULT_CHAIN_PARSER,
                **storage_options: Any,
            ) -> WindowsUPath:
                raise UnsupportedOperation(
                    f"cannot instantiate {cls.__name__} on your system"
                )

    class PosixUPath(LocalPath, pathlib.PosixPath):
        __slots__ = ()

        if os.name == "nt":

            def __new__(
                cls,
                *args,
                protocol: str | None = None,
                chain_parser: FSSpecChainParser = DEFAULT_CHAIN_PARSER,
                **storage_options: Any,
            ) -> PosixUPath:
                raise UnsupportedOperation(
                    f"cannot instantiate {cls.__name__} on your system"
                )


class FilePath(UPath):
    __slots__ = ()

    if TYPE_CHECKING:

        def __init__(
            self,
            *args: JoinablePathLike,
            protocol: Literal["file", "local"] | None = ...,
            chain_parser: FSSpecChainParser = ...,
            **storage_options: Unpack[FileStorageOptions],
        ) -> None: ...

    def __fspath__(self) -> str:
        return self.path

    def iterdir(self) -> Iterator[Self]:
        if _LISTDIR_WORKS_ON_FILES is None:
            _check_listdir_works_on_files()
        elif _LISTDIR_WORKS_ON_FILES and self.is_file():
            raise NotADirectoryError(f"{self}")
        return super().iterdir()

    @property
    def _url(self) -> SplitResult:
        return SplitResult._make((self.protocol, "", self.path, "", ""))

    @classmethod
    def cwd(cls) -> Self:
        return cls(os.getcwd(), protocol="file")

    @classmethod
    def home(cls) -> Self:
        return cls(os.path.expanduser("~"), protocol="file")

    def chmod(
        self,
        mode: int,
        *,
        follow_symlinks: bool = True,
    ) -> None:
        return os.chmod(self.path, mode, follow_symlinks=follow_symlinks)


LocalPath.register(FilePath)
