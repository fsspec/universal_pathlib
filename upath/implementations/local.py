from __future__ import annotations

import os
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
    pass


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


class PosixUPath(PosixPath, UPath):
    __slots__ = ()

    if os.name == "nt":
        __new__ = PosixPath.__new__

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


class WindowsUPath(WindowsPath, UPath):
    __slots__ = ()

    if os.name != "nt":
        __new__ = WindowsPath.__new__

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
