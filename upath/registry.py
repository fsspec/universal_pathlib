"""upath.registry -- registry for file system specific implementations

Retrieve UPath implementations via `get_upath_class`.
Register custom UPath subclasses in one of two ways:

### directly from Python

>>> from upath import UPath
>>> from upath.registry import register_implementation
>>> my_protocol = "myproto"
>>> class MyPath(UPath):
...     pass
>>> register_implementation(my_protocol, MyPath)

### via entry points

```toml
# pyproject.toml
[project.entry-points."universal_pathlib.implementations"]
myproto = "my_module.submodule:MyPath"
```

```ini
# setup.cfg
[options.entry_points]
universal_pathlib.implementations =
    myproto = my_module.submodule:MyPath
```
"""

from __future__ import annotations

import os
import re
import sys
import warnings
from collections import ChainMap
from collections.abc import Iterator
from collections.abc import MutableMapping
from functools import lru_cache
from importlib import import_module
from importlib.metadata import entry_points
from typing import TYPE_CHECKING

from fsspec.core import get_filesystem_class
from fsspec.registry import known_implementations as _fsspec_known_implementations
from fsspec.registry import registry as _fsspec_registry

import upath

if TYPE_CHECKING:
    from typing import Literal
    from typing import overload

    from upath.implementations.cached import SimpleCachePath as _SimpleCachePath
    from upath.implementations.cloud import AzurePath as _AzurePath
    from upath.implementations.cloud import GCSPath as _GCSPath
    from upath.implementations.cloud import HfPath as _HfPath
    from upath.implementations.cloud import S3Path as _S3Path
    from upath.implementations.data import DataPath as _DataPath
    from upath.implementations.ftp import FTPPath as _FTPPath
    from upath.implementations.github import GitHubPath as _GitHubPath
    from upath.implementations.hdfs import HDFSPath as _HDFSPath
    from upath.implementations.http import HTTPPath as _HTTPPath
    from upath.implementations.local import FilePath as _FilePath
    from upath.implementations.local import PosixUPath as _PosixUPath
    from upath.implementations.local import WindowsUPath as _WindowsUPath
    from upath.implementations.memory import MemoryPath as _MemoryPath
    from upath.implementations.sftp import SFTPPath as _SFTPPath
    from upath.implementations.smb import SMBPath as _SMBPath
    from upath.implementations.tar import TarPath as _TarPath
    from upath.implementations.webdav import WebdavPath as _WebdavPath
    from upath.implementations.zip import ZipPath as _ZipPath


__all__ = [
    "get_upath_class",
    "available_implementations",
    "register_implementation",
]


_ENTRY_POINT_GROUP = "universal_pathlib.implementations"


class _Registry(MutableMapping[str, "type[upath.UPath]"]):
    """internal registry for UPath subclasses"""

    known_implementations: dict[str, str] = {
        "abfs": "upath.implementations.cloud.AzurePath",
        "abfss": "upath.implementations.cloud.AzurePath",
        "adl": "upath.implementations.cloud.AzurePath",
        "az": "upath.implementations.cloud.AzurePath",
        "data": "upath.implementations.data.DataPath",
        "file": "upath.implementations.local.FilePath",
        "ftp": "upath.implementations.ftp.FTPPath",
        "local": "upath.implementations.local.FilePath",
        "gcs": "upath.implementations.cloud.GCSPath",
        "gs": "upath.implementations.cloud.GCSPath",
        "hdfs": "upath.implementations.hdfs.HDFSPath",
        "hf": "upath.implementations.cloud.HfPath",
        "http": "upath.implementations.http.HTTPPath",
        "https": "upath.implementations.http.HTTPPath",
        "memory": "upath.implementations.memory.MemoryPath",
        "s3": "upath.implementations.cloud.S3Path",
        "s3a": "upath.implementations.cloud.S3Path",
        "simplecache": "upath.implementations.cached.SimpleCachePath",
        "sftp": "upath.implementations.sftp.SFTPPath",
        "ssh": "upath.implementations.sftp.SFTPPath",
        "tar": "upath.implementations.tar.TarPath",
        "webdav": "upath.implementations.webdav.WebdavPath",
        "webdav+http": "upath.implementations.webdav.WebdavPath",
        "webdav+https": "upath.implementations.webdav.WebdavPath",
        "github": "upath.implementations.github.GitHubPath",
        "smb": "upath.implementations.smb.SMBPath",
        "zip": "upath.implementations.zip.ZipPath",
    }

    if TYPE_CHECKING:
        _m: MutableMapping[str, str | type[upath.UPath]]

    def __init__(self) -> None:
        if sys.version_info >= (3, 10):
            eps = entry_points(group=_ENTRY_POINT_GROUP)
        else:
            eps = entry_points().get(_ENTRY_POINT_GROUP, [])
        self._entries = {ep.name: ep for ep in eps}
        self._m = ChainMap({}, self.known_implementations)  # type: ignore

    def __contains__(self, item: object) -> bool:
        return item in set().union(self._m, self._entries)

    def __getitem__(self, item: str) -> type[upath.UPath]:
        fqn: str | type[upath.UPath] | None = self._m.get(item)
        if fqn is None:
            if item in self._entries:
                fqn = self._m[item] = self._entries[item].load()
        if fqn is None:
            raise KeyError(f"{item} not in registry")
        if isinstance(fqn, str):
            module_name, name = fqn.rsplit(".", 1)
            mod = import_module(module_name)
            cls = getattr(mod, name)  # type: ignore
        else:
            cls = fqn
        return cls

    def __setitem__(self, item: str, value: type[upath.UPath] | str) -> None:
        if not (
            (isinstance(value, type) and issubclass(value, upath.UPath))
            or isinstance(value, str)
        ):
            raise ValueError(
                f"expected UPath subclass or FQN-string, got: {type(value).__name__!r}"
            )
        if not item or item in self._m:
            get_upath_class.cache_clear()  # type: ignore[attr-defined]
        self._m[item] = value

    def __delitem__(self, __v: str) -> None:
        raise NotImplementedError("removal is unsupported")

    def __len__(self) -> int:
        return len(set().union(self._m, self._entries))

    def __iter__(self) -> Iterator[str]:
        return iter(set().union(self._m, self._entries))


_registry = _Registry()


def available_implementations(*, fallback: bool = False) -> list[str]:
    """return a list of protocols for available implementations

    Parameters
    ----------
    fallback:
        If True, also return protocols for fsspec filesystems without
        an implementation in universal_pathlib.
    """
    if not fallback:
        return list(_registry)
    else:
        return list({*_registry, *_fsspec_registry, *_fsspec_known_implementations})


def register_implementation(
    protocol: str,
    cls: type[upath.UPath] | str,
    *,
    clobber: bool = False,
) -> None:
    """register a UPath implementation with a protocol

    Parameters
    ----------
    protocol:
        Protocol name to associate with the class
    cls:
        The UPath subclass for the protocol or a str representing the
        full path to an implementation class like package.module.class.
    clobber:
        Whether to overwrite a protocol with the same name; if False,
        will raise instead.
    """
    if not re.match(r"^[a-z][a-z0-9+_.]+$", protocol):
        raise ValueError(f"{protocol!r} is not a valid URI scheme")
    if not clobber and protocol in _registry:
        raise ValueError(f"{protocol!r} is already in registry and clobber is False!")
    _registry[protocol] = cls


# --- get_upath_class type overloads ------------------------------------------

if TYPE_CHECKING:  # noqa: C901

    @overload
    def get_upath_class(protocol: Literal["simplecache"]) -> type[_SimpleCachePath]: ...
    @overload
    def get_upath_class(protocol: Literal["s3", "s3a"]) -> type[_S3Path]: ...
    @overload
    def get_upath_class(protocol: Literal["gcs", "gs"]) -> type[_GCSPath]: ...
    @overload  # noqa: E301
    def get_upath_class(
        protocol: Literal["abfs", "abfss", "adl", "az"],
    ) -> type[_AzurePath]: ...
    @overload
    def get_upath_class(protocol: Literal["data"]) -> type[_DataPath]: ...
    @overload
    def get_upath_class(protocol: Literal["ftp"]) -> type[_FTPPath]: ...
    @overload
    def get_upath_class(protocol: Literal["github"]) -> type[_GitHubPath]: ...
    @overload
    def get_upath_class(protocol: Literal["hdfs"]) -> type[_HDFSPath]: ...
    @overload
    def get_upath_class(protocol: Literal["hf"]) -> type[_HfPath]: ...
    @overload
    def get_upath_class(protocol: Literal["http", "https"]) -> type[_HTTPPath]: ...
    @overload
    def get_upath_class(protocol: Literal["file", "local"]) -> type[_FilePath]: ...
    @overload
    def get_upath_class(protocol: Literal["memory"]) -> type[_MemoryPath]: ...
    @overload
    def get_upath_class(protocol: Literal["sftp", "ssh"]) -> type[_SFTPPath]: ...
    @overload
    def get_upath_class(protocol: Literal["smb"]) -> type[_SMBPath]: ...
    @overload
    def get_upath_class(protocol: Literal["tar"]) -> type[_TarPath]: ...
    @overload
    def get_upath_class(protocol: Literal["webdav"]) -> type[_WebdavPath]: ...
    @overload
    def get_upath_class(protocol: Literal["zip"]) -> type[_ZipPath]: ...

    if sys.platform == "win32":

        @overload
        def get_upath_class(protocol: Literal[""]) -> type[_WindowsUPath]: ...

    else:

        @overload
        def get_upath_class(protocol: Literal[""]) -> type[_PosixUPath]: ...  # type: ignore[overload-overlap]  # noqa: E501

    @overload
    def get_upath_class(
        protocol: str, *, fallback: bool = ...
    ) -> type[upath.UPath] | None: ...


@lru_cache  # type: ignore[misc] # see: https://github.com/python/typeshed/issues/11280
def get_upath_class(
    protocol: str,
    *,
    fallback: bool = True,
) -> type[upath.UPath] | None:
    """Return the upath cls for the given protocol.

    Returns `None` if no matching protocol can be found.

    Parameters
    ----------
    protocol:
        The protocol string
    fallback:
        If fallback is False, don't return UPath instances for fsspec
        filesystems that don't have an implementation registered.
    """
    try:
        return _registry[protocol]
    except KeyError:
        if not protocol:
            if os.name == "nt":
                from upath.implementations.local import WindowsUPath

                return WindowsUPath  # type: ignore[return-value]
            else:
                from upath.implementations.local import PosixUPath

                return PosixUPath  # type: ignore[return-value]
        if not fallback:
            return None
        try:
            get_filesystem_class(protocol)
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
            import upath.implementations._experimental as upath_experimental

            cls_name = f"_{protocol.title()}Path"
            cls = type(
                cls_name,
                (upath.UPath,),
                {"__module__": "upath.implementations._experimental"},
            )
            setattr(upath_experimental, cls_name, cls)
            return cls
