from __future__ import annotations

import sys
from pathlib import PosixPath
from pathlib import WindowsPath
from typing import Any
from urllib.parse import SplitResult

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from upath._uris import compatible_protocol
from upath.core import UPath
from upath.core import UPathLike

__all__ = [
    "LocalPath",
    "FilePath",
    "PosixUPath",
    "WindowsUPath",
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


class LocalPath(UPath):
    __slots__ = ()


class FilePath(LocalPath):
    __slots__ = ()

    def iterdir(self):
        if _LISTDIR_WORKS_ON_FILES is None:
            _check_listdir_works_on_files()
        if _LISTDIR_WORKS_ON_FILES and self.is_file():
            raise NotADirectoryError(f"{self}")
        return super().iterdir()

    @property
    def path(self):
        sep = self.parser.sep
        if self.drive:
            return f"/{super().path}".replace(sep, "/")
        return super().path.replace(sep, "/")

    @property
    def _url(self):
        return SplitResult(self.protocol, "", self.path, "", "")


class PosixUPath(PosixPath):
    __slots__ = (
        "_protocol",
        "_storage_options",
        "_fs_cached",
    )

    def __new__(
        cls,
        path: UPathLike,
        *paths: UPathLike,
        protocol: str | None = None,
        **storage_options: Any,
    ) -> Self:
        if not compatible_protocol("", path, *paths):
            raise ValueError("can't combine incompatible UPath protocols")
        obj = super().__new__(cls, str(path), *map(str, paths))
        obj._protocol = ""
        obj._storage_options = {}
        return obj

    if sys.version_info >= (3, 12):

        def __init__(
            self,
            path: UPathLike,
            *paths: UPathLike,
            protocol: str | None = None,
            **storage_options: Any,
        ) -> None:
            super().__init__(str(path), *map(str, paths))

    protocol = UPath.protocol
    storage_options = UPath.storage_options
    joinuri = UPath.joinuri
    fs = UPath.fs
    _fs_factory = UPath._fs_factory
    _url = UPath._url

    @property
    def path(self) -> str:
        return PosixPath.__str__(self)


class WindowsUPath(WindowsPath):
    __slots__ = (
        "_protocol",
        "_storage_options",
        "_fs_cached",
    )

    def __new__(
        cls,
        path: UPathLike,
        *paths: UPathLike,
        protocol: str | None = None,
        **storage_options: Any,
    ) -> Self:
        if not compatible_protocol("", path, *paths):
            raise ValueError("can't combine incompatible UPath protocols")
        obj = super().__new__(cls, str(path), *map(str, paths))
        obj._protocol = ""
        obj._storage_options = {}
        return obj

    if sys.version_info >= (3, 12):

        def __init__(
            self,
            path: UPathLike,
            *paths: UPathLike,
            protocol: str | None = None,
            **storage_options: Any,
        ) -> None:
            super().__init__(str(path), *map(str, paths))

    protocol = UPath.protocol
    storage_options = UPath.storage_options
    joinuri = UPath.joinuri
    fs = UPath.fs
    _fs_factory = UPath._fs_factory
    _url = UPath._url

    @property
    def path(self) -> str:
        return WindowsPath.__str__(self)


UPath.register(PosixUPath)  # type: ignore[attr-defined]
UPath.register(WindowsUPath)  # type: ignore[attr-defined]
LocalPath.register(PosixUPath)  # type: ignore[attr-defined]
LocalPath.register(WindowsUPath)  # type: ignore[attr-defined]
