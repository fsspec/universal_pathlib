from __future__ import annotations

import importlib
import warnings
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from fsspec.core import get_filesystem_class

if TYPE_CHECKING:
    from upath.core import PT

__all__ = [
    "get_upath_class",
]


class _Registry:
    known_implementations: dict[str, str] = {
        "abfs": "upath.implementations.cloud.AzurePath",
        "abfss": "upath.implementations.cloud.AzurePath",
        "adl": "upath.implementations.cloud.AzurePath",
        "az": "upath.implementations.cloud.AzurePath",
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

    def __getitem__(self, item: str) -> type[PT] | None:
        try:
            fqn = self.known_implementations[item]
        except KeyError:
            return None
        module_name, name = fqn.rsplit(".", 1)
        mod = importlib.import_module(module_name)
        return getattr(mod, name)  # type: ignore


_registry = _Registry()


@lru_cache
def get_upath_class(protocol: str) -> type[PT] | type[Path] | None:
    """Return the upath cls for the given protocol."""
    cls: type[PT] | None = _registry[protocol]
    if cls is not None:
        return cls
    else:
        if not protocol:
            return None  # we want to use pathlib for `None` protocol
        try:
            _fs_cls = get_filesystem_class(protocol)
        except ValueError:
            return None  # this is an unknown protocol
        else:
            if _fs_cls.protocol != "file":
                warnings.warn(
                    f"UPath {protocol!r} filesystem not explicitly implemented."
                    " Falling back to default implementation."
                    " This filesystem may not be tested.",
                    UserWarning,
                    stacklevel=2,
                )
            mod = importlib.import_module("upath.core")
            return mod.UPath  # type: ignore
