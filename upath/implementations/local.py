import os
from pathlib import PosixPath
from pathlib import WindowsPath

from upath.core import UPath


class LocalPath(UPath):
    pass


class PosixUPath(PosixPath, UPath):
    __slots__ = ()

    if os.name == "nt":
        __new__ = PosixPath.__new__

    @property
    def fs(self):
        try:
            return self._cached_fs
        except AttributeError:
            from fsspec.implementations.local import LocalFileSystem

            self._cached_fs = fs = LocalFileSystem()
            return fs

    @property
    def path(self) -> str:
        return str(self)


class WindowsUPath(WindowsPath, UPath):
    __slots__ = ()

    if os.name != "nt":
        __new__ = WindowsPath.__new__

    @property
    def fs(self):
        try:
            return self._cached_fs
        except AttributeError:
            from fsspec.implementations.local import LocalFileSystem

            self._cached_fs = fs = LocalFileSystem()
            return fs

    @property
    def path(self) -> str:
        return str(self)
