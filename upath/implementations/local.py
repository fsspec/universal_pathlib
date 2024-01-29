from __future__ import annotations

import os
import sys
from inspect import ismemberdescriptor
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
    "FilePath",
    "PosixUPath",
    "WindowsUPath",
]


class LocalPath(UPath):
    __slots__ = ()


class FilePath(LocalPath):
    __slots__ = ()


_PY310_IGNORE = {"__slots__", "__module__", "_from_parts", "__new__"}


def _iterate_class_attrs(
    path_cls: type[Path],
    ignore: set[str] = frozenset(),
) -> Iterable[tuple[str, Any]]:
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


class PosixUPath(PosixPath, LocalPath):
    __slots__ = ()

    if os.name == "nt":
        __new__ = PosixPath.__new__  # type: ignore

    # assign all PosixPath methods/attrs to prevent multi inheritance issues
    for attr, func_or_attr in _iterate_class_attrs(PosixPath, ignore=_PY310_IGNORE):
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

    @classmethod
    def _from_parsed_parts(
        cls,
        drv,
        root,
        parts,
        url=None,
        **kwargs: Any,
    ):
        obj = super(UPath, cls)._from_parsed_parts(  # type: ignore[misc]
            drv, root, parts
        )
        obj._kwargs = {}
        obj._url = SplitResult("", "", str(obj), "", "")
        return obj


class WindowsUPath(WindowsPath, LocalPath):
    __slots__ = ()

    if os.name != "nt":
        __new__ = WindowsPath.__new__  # type: ignore

    # assign all WindowsPath methods/attrs to prevent multi inheritance issues
    for attr, func_or_attr in _iterate_class_attrs(WindowsPath, ignore=_PY310_IGNORE):
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

    @classmethod
    def _from_parsed_parts(
        cls,
        drv,
        root,
        parts,
        url=None,
        **kwargs: Any,
    ):
        obj = super(UPath, cls)._from_parsed_parts(  # type: ignore[misc]
            drv, root, parts
        )
        obj._kwargs = {}
        obj._url = SplitResult("", "", str(obj), "", "")
        return obj


if sys.version_info >= (3, 12):  # noqa: C901
    from upath.core312plus import FSSpecFlavour

    class LocalPath(UPath):
        __slots__ = ()
        _flavour = FSSpecFlavour(
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

    class FilePath(LocalPath):  # noqa
        __slots__ = ()

    _PY312_IGNORE = {"__slots__", "__module__", "__new__", "__init__", "with_segments"}

    class PosixUPath(PosixPath, LocalPath):  # noqa
        __slots__ = ()

        if os.name == "nt":
            __new__ = PosixPath.__new__

        # assign all PosixPath methods/attrs to prevent multi inheritance issues
        for attr, func_or_attr in _iterate_class_attrs(PosixPath, ignore=_PY312_IGNORE):
            locals()[attr] = func_or_attr
        del attr, func_or_attr

    class WindowsUPath(WindowsPath, LocalPath):  # noqa
        __slots__ = ()

        if os.name != "nt":
            __new__ = WindowsPath.__new__

        # assign all WindowsPath methods/attrs to prevent multi inheritance issues
        for attr, func_or_attr in _iterate_class_attrs(
            WindowsPath, ignore=_PY312_IGNORE
        ):
            locals()[attr] = func_or_attr
        del attr, func_or_attr
