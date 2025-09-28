from __future__ import annotations

import os
import pathlib
import sys
import warnings
from collections.abc import Iterator
from collections.abc import Sequence
from typing import TYPE_CHECKING
from typing import Any
from urllib.parse import SplitResult

from fsspec import AbstractFileSystem

from upath._chain import DEFAULT_CHAIN_PARSER
from upath._chain import Chain
from upath._chain import ChainSegment
from upath._chain import FSSpecChainParser
from upath._protocol import compatible_protocol
from upath.core import UPath
from upath.core import _UPathMixin
from upath.types import JoinablePathLike

if TYPE_CHECKING:
    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self

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


UPath.register(LocalPath)


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
            raise NotImplementedError(
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
            raise NotImplementedError(
                f"cannot instantiate {cls.__name__} on your system"
            )


class FilePath(UPath):
    __slots__ = ()

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


LocalPath.register(FilePath)
