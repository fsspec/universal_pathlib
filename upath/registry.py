from __future__ import annotations

import os
import sys
import warnings
from collections import ChainMap
from functools import lru_cache
from importlib import import_module
from importlib.metadata import entry_points
from typing import Any
from typing import Iterator
from typing import MutableMapping

from fsspec.core import get_filesystem_class
from fsspec.registry import available_protocols

import upath.core

__all__ = [
    "get_upath_class",
    "available_implementations",
    "register_implementation",
]


class _Registry(MutableMapping[str, "type[upath.core.UPath]"]):
    """internal registry for UPath subclasses"""

    known_implementations: dict[str, str] = {
        "abfs": "upath.implementations.cloud.AzurePath",
        "abfss": "upath.implementations.cloud.AzurePath",
        "adl": "upath.implementations.cloud.AzurePath",
        "az": "upath.implementations.cloud.AzurePath",
        "file": "upath.implementations.local.LocalPath",
        "gcs": "upath.implementations.cloud.GCSPath",
        "gs": "upath.implementations.cloud.GCSPath",
        "hdfs": "upath.implementations.hdfs.HDFSPath",
        "http": "upath.implementations.http.HTTPPath",
        "https": "upath.implementations.http.HTTPPath",
        "memory": "upath.implementations.memory.MemoryPath",
        "s3": "upath.implementations.cloud.S3Path",
        "s3a": "upath.implementations.cloud.S3Path",
        "webdav+http": "upath.implementations.webdav.WebdavPath",
        "webdav+https": "upath.implementations.webdav.WebdavPath",
    }

    def __init__(self) -> None:
        if sys.version_info >= (3, 10):
            eps = entry_points(group="universal_pathlib.implementations")
        else:
            eps = entry_points()["universal_pathlib.implementations"]
        ep_dct: dict[str, Any] = {ep.name: ep for ep in eps}
        self._m = ChainMap({}, ep_dct, self.known_implementations)

    def __getitem__(self, item: str) -> type[upath.core.UPath]:
        fqn = self._m[item]
        if isinstance(fqn, str):
            module_name, name = fqn.rsplit(".", 1)
            mod = import_module(module_name)
            cls = getattr(mod, name)  # type: ignore
        elif hasattr(fqn, "load"):
            cls = fqn.load()
        else:
            cls = fqn

        if not issubclass(cls, upath.core.UPath):
            raise TypeError(f"expected UPath subclass, got: {cls.__name__!r}")
        return cls

    def __setitem__(self, item: str, value: type[upath.core.UPath] | str) -> None:
        if not (issubclass(value, upath.core.UPath) or isinstance(value, str)):
            raise ValueError(
                f"expected UPath subclass or FQN-string, got: {type(value).__name__!r}"
            )
        self._m[item] = value

    def __delitem__(self, __v: str) -> None:
        raise NotImplementedError("removal is unsupported")

    def __len__(self) -> int:
        return len(self._m)

    def __iter__(self) -> Iterator[str]:
        return iter(self._m)


_registry = _Registry()


def available_implementations(include_default: bool = False) -> list[str]:
    """return the available implementations"""
    impl = list(_registry)
    if not include_default:
        return impl
    else:
        return list({*impl, *available_protocols()})


def register_implementation(
    protocol: str,
    cls: type[upath.core.UPath],
    *,
    clobber: bool = False,
) -> None:
    """register a UPath implementation with a protocol

    Parameters
    ----------
    protocol:
        Protocol name to associate with the class
    cls:
        The UPath subclass for the protocol


    """
    if not clobber and protocol in _registry:
        raise ValueError(f"{protocol!r} is already in registry and clobber is False!")
    _registry[protocol] = cls


@lru_cache
def get_upath_class(protocol: str) -> type[upath.core.UPath] | None:
    """Return the upath cls for the given protocol."""
    try:
        return _registry[protocol]
    except KeyError:
        if not protocol:
            if os.name == "nt":
                from upath.implementations.local import WindowsUPath

                return WindowsUPath
            else:
                from upath.implementations.local import PosixUPath

                return PosixUPath
        try:
            _ = get_filesystem_class(protocol)
        except ValueError:
            return None  # this is an unknown protocol
        else:
            warnings.warn(
                f"UPath {protocol!r} filesystem not explicitly implemented."
                " Falling back to default implementation."
                " This filesystem may not be tested.",
                UserWarning,
                stacklevel=2,
            )
            return upath.core.UPath
