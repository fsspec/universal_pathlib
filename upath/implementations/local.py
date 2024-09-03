from __future__ import annotations

from pathlib import PosixPath
from pathlib import WindowsPath
from typing import Any
from urllib.parse import SplitResult

from upath.core import UPath

__all__ = [
    "LocalPath",
    "FilePath",
    "PosixUPath",
    "WindowsUPath",
]

from upath.core import UPathLike

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

    def __init__(
        self,
        path: UPathLike,
        *paths: UPathLike,
        protocol: str | None = None,
        **storage_options: Any,
    ) -> None:
        super().__init__(path, *paths)
        self._protocol = ""
        self._storage_options = {}

    protocol = UPath.protocol
    storage_options = UPath.storage_options

    @property
    def path(self) -> str:
        return PosixPath.__str__(self)

    joinuri = UPath.joinuri
    _url = UPath._url
    fs = UPath.fs


class WindowsUPath(WindowsPath):
    __slots__ = (
        "_protocol",
        "_storage_options",
        "_fs_cached",
    )

    def __init__(
        self,
        path: UPathLike,
        *paths: UPathLike,
        protocol: str | None = None,
        **storage_options: Any,
    ) -> None:
        super().__init__(path, *paths)
        self._protocol = ""
        self._storage_options = {}

    protocol = UPath.protocol
    storage_options = UPath.storage_options

    @property
    def path(self) -> str:
        return PosixPath.__str__(self)

    joinuri = UPath.joinuri
    _url = UPath._url
    fs = UPath.fs


UPath.register(PosixUPath)
UPath.register(WindowsUPath)
LocalPath.register(PosixUPath)
LocalPath.register(WindowsUPath)
