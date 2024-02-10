from __future__ import annotations

import os
import sys
from inspect import ismemberdescriptor
from pathlib import Path
from pathlib import PosixPath
from pathlib import WindowsPath
from typing import Any
from typing import Collection
from typing import MutableMapping
from urllib.parse import SplitResult

from fsspec import __version__ as fsspec_version
from packaging.version import Version

from upath._flavour import FSSpecFlavour as _FSSpecFlavour
from upath.core import UPath

__all__ = [
    "LocalPath",
    "FilePath",
    "PosixUPath",
    "WindowsUPath",
]

_LISTDIR_WORKS_ON_FILES = Version(fsspec_version) >= Version("2024.2.0")


class LocalPath(UPath):
    __slots__ = ()
    _flavour = _FSSpecFlavour(
        posixpath_only=False,
    )

    @property
    def path(self):
        sep = self._flavour.sep
        if self.drive:
            return f"/{super().path}".replace(sep, "/")
        return super().path.replace(sep, "/")

    @property
    def _url(self):
        return SplitResult(self.protocol, "", self.path, "", "")


class FilePath(LocalPath):
    __slots__ = ()

    def iterdir(self):
        if _LISTDIR_WORKS_ON_FILES and self.is_file():
            raise NotADirectoryError(f"{self}")
        return super().iterdir()


_pathlib_py312_ignore = {
    "__slots__",
    "__module__",
    "__new__",
    "__init__",
    "_from_parts",
    "_from_parsed_parts",
    "with_segments",
}


def _set_class_attributes(
    type_dict: MutableMapping[str, Any],
    src: type[Path],
    *,
    ignore: Collection[str] = frozenset(_pathlib_py312_ignore),
) -> None:
    """helper function to assign all methods/attrs from src to a class dict"""
    visited = set()
    for cls in src.__mro__:
        if cls is object:
            continue
        for attr, func_or_value in cls.__dict__.items():
            if ismemberdescriptor(func_or_value):
                continue
            if attr in ignore or attr in visited:
                continue
            else:
                visited.add(attr)

            type_dict[attr] = func_or_value


def _upath_init(inst: PosixUPath | WindowsUPath) -> None:
    """helper to initialize the PosixPath/WindowsPath instance with UPath attrs"""
    inst._protocol = ""
    inst._storage_options = {}
    if sys.version_info < (3, 10):
        inst._init()


class PosixUPath(PosixPath, LocalPath):
    __slots__ = ()

    # assign all PosixPath methods/attrs to prevent multi inheritance issues
    _set_class_attributes(locals(), src=PosixPath)

    if sys.version_info < (3, 12):

        def __new__(
            cls, *args, protocol: str | None = None, **storage_options: Any
        ) -> UPath:
            if os.name == "nt":
                raise NotImplementedError(
                    f"cannot instantiate {cls.__name__} on your system"
                )
            obj = super().__new__(cls, *args)
            obj._protocol = ""
            return obj

        def __init__(
            self, *args, protocol: str | None = None, **storage_options: Any
        ) -> None:
            super(Path, self).__init__()
            self._drv, self._root, self._parts = type(self)._parse_args(args)
            _upath_init(self)

        @classmethod
        def _from_parts(cls, *args, **kwargs):
            obj = super(Path, cls)._from_parts(*args, **kwargs)
            _upath_init(obj)
            return obj

        @classmethod
        def _from_parsed_parts(cls, drv, root, parts):
            obj = super(Path, cls)._from_parsed_parts(drv, root, parts)
            _upath_init(obj)
            return obj

        @property
        def path(self) -> str:
            return PosixPath.__str__(self)


class WindowsUPath(WindowsPath, LocalPath):
    __slots__ = ()

    # assign all WindowsPath methods/attrs to prevent multi inheritance issues
    _set_class_attributes(locals(), src=WindowsPath)

    if sys.version_info < (3, 12):

        def __new__(
            cls, *args, protocol: str | None = None, **storage_options: Any
        ) -> UPath:
            if os.name != "nt":
                raise NotImplementedError(
                    f"cannot instantiate {cls.__name__} on your system"
                )
            obj = super().__new__(cls, *args)
            obj._protocol = ""
            return obj

        def __init__(
            self, *args, protocol: str | None = None, **storage_options: Any
        ) -> None:
            super(Path, self).__init__()
            self._drv, self._root, self._parts = self._parse_args(args)
            _upath_init(self)

        @classmethod
        def _from_parts(cls, *args, **kwargs):
            obj = super(Path, cls)._from_parts(*args, **kwargs)
            _upath_init(obj)
            return obj

        @classmethod
        def _from_parsed_parts(cls, drv, root, parts):
            obj = super(Path, cls)._from_parsed_parts(drv, root, parts)
            _upath_init(obj)
            return obj

        @property
        def path(self) -> str:
            return WindowsPath.__str__(self)
