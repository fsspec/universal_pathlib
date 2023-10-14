from __future__ import annotations

import os
import sys
from pathlib import Path
from pathlib import PosixPath
from pathlib import WindowsPath
from typing import Any
from typing import Iterable
from urllib.parse import SplitResult

from fsspec.implementations.local import LocalFileSystem

from upath.core import UPath

__all__ = [
    "LocalPath",
    "PosixUPath",
    "WindowsUPath",
]


class LocalPath(UPath):
    __slots__ = ()


class FilePath(LocalPath):
    __slots__ = ()


def _iterate_class_attrs(path_cls: type[Path]) -> Iterable[tuple[str, Any]]:
    ignore = {"__slots__", "__module__", "_from_parts", "__new__"}
    visited = set()
    for cls in path_cls.__mro__:
        for attr, func_or_value in cls.__dict__.items():
            if attr in ignore:
                continue
            if attr in visited:
                continue

            yield attr, func_or_value
            visited.add(attr)


class PosixUPath(PosixPath, LocalPath):
    __slots__ = ()

    if os.name == "nt":
        __new__ = PosixPath.__new__  # type: ignore

    # assign all PosixPath methods/attrs to prevent multi inheritance issues
    for attr, func_or_attr in _iterate_class_attrs(PosixPath):
        locals()[attr] = func_or_attr
    del attr, func_or_attr

    @property
    def fs(self):
        return LocalFileSystem()

    @property
    def path(self) -> str:
        return str(self)

    @classmethod
    def _from_parts(cls, args, *, url=None, **kw):
        obj = super(UPath, cls)._from_parts(args)
        obj._kwargs = {}
        obj._url = SplitResult("", "", str(obj), "", "")
        return obj


class WindowsUPath(WindowsPath, LocalPath):
    __slots__ = ()

    if os.name != "nt":
        __new__ = WindowsPath.__new__  # type: ignore

    # assign all WindowsPath methods/attrs to prevent multi inheritance issues
    for attr, func_or_attr in _iterate_class_attrs(WindowsPath):
        locals()[attr] = func_or_attr
    del attr, func_or_attr

    @property
    def fs(self):
        return LocalFileSystem()

    @property
    def path(self) -> str:
        return str(self)

    @classmethod
    def _from_parts(cls, args, *, url=None, **kw):
        obj = super(UPath, cls)._from_parts(args)
        obj._kwargs = {}
        obj._url = SplitResult("", "", str(obj), "", "")
        return obj


if sys.version_info >= (3, 12):  # noqa: C901
    from inspect import ismemberdescriptor
    from urllib.parse import urlsplit

    from upath.core312plus import PathOrStr
    from upath.core312plus import fsspecpathmod
    from upath.core312plus import strip_upath_protocol

    class filepathmod(fsspecpathmod):
        @staticmethod
        def splitroot(__path: PathOrStr) -> tuple[str, str, str]:
            path = strip_upath_protocol(__path)
            drv, root, path = os.path.splitroot(path)  # type: ignore
            if os.name == "nt" and not drv:
                drv = "C:"
            return drv, root, path

        @staticmethod
        def splitdrive(__path: PathOrStr) -> tuple[str, str]:
            path = strip_upath_protocol(__path)
            drv, path = os.path.splitdrive(path)
            if os.name == "nt" and not drv:
                drv = "C:"
            return drv, path

        @staticmethod
        def normcase(__path: PathOrStr) -> str:
            return os.path.normcase(__path)

    class LocalPath(UPath):
        __slots__ = ()
        pathmod = _flavour = filepathmod

        @property
        def path(self):
            sep = self._flavour.sep
            if self.drive:
                return f"/{super().path}".replace(sep, "/")
            return super().path.replace(sep, "/")

        @property
        def _url(self):  # todo: deprecate
            return urlsplit(f"file:{self.path}")._replace(scheme=self.protocol)

    class FilePath(LocalPath):  # noqa
        __slots__ = ()

    def _iterate_class_attrs(path_cls: type[Path]) -> Iterable[tuple[str, Any]]:
        ignore = {
            "__slots__",
            "__module__",
            "__new__",
            "__init__",
            "with_segments",
            "pathmod",
            "_flavour",
        }
        visited = set()
        for cls in path_cls.__mro__:
            if cls is object:
                continue
            for attr, func_or_value in cls.__dict__.items():
                if attr in ignore:
                    continue
                if attr in visited:
                    continue
                if ismemberdescriptor(func_or_value):
                    continue

                yield attr, func_or_value
                visited.add(attr)

    class PosixUPath(PosixPath, LocalPath):  # noqa
        __slots__ = ()
        pathmod = _flavour = PosixPath._flavour

        if os.name == "nt":
            __new__ = PosixPath.__new__

        # assign all PosixPath methods/attrs to prevent multi inheritance issues
        for attr, func_or_attr in _iterate_class_attrs(PosixPath):
            locals()[attr] = func_or_attr
        del attr, func_or_attr

    class WindowsUPath(WindowsPath, LocalPath):  # noqa
        __slots__ = ()
        pathmod = _flavour = WindowsPath._flavour

        if os.name != "nt":
            __new__ = WindowsPath.__new__

        # assign all WindowsPath methods/attrs to prevent multi inheritance issues
        for attr, func_or_attr in _iterate_class_attrs(WindowsPath):
            locals()[attr] = func_or_attr
        del attr, func_or_attr
