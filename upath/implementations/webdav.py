from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

from fsspec.registry import known_implementations
from fsspec.registry import register_implementation

from upath._compat import FSSpecAccessorShim as _FSSpecAccessorShim
from upath._compat import str_remove_prefix
from upath._compat import str_remove_suffix
from upath.core import UPath

__all__ = [
    "WebdavPath",
]

# webdav was only registered in fsspec>=2022.5.0
if "webdav" not in known_implementations:
    import webdav4.fsspec

    register_implementation("webdav", webdav4.fsspec.WebdavFileSystem)


# accessors are deprecated
_WebdavAccessor = _FSSpecAccessorShim


class WebdavPath(UPath):
    __slots__ = ()

    def __init__(
        self, *args, protocol: str | None = None, **storage_options: Any
    ) -> None:
        base_options = getattr(self, "_storage_options", {})  # when unpickling
        if args:
            args0, *argsN = args
            url = urlsplit(str(args0))
            args0 = urlunsplit(url._replace(scheme="", netloc="")) or "/"
            if "base_url" not in storage_options:
                if self._protocol == "webdav+http":
                    storage_options["base_url"] = urlunsplit(
                        url._replace(scheme="http", path="")
                    )
                elif self._protocol == "webdav+https":
                    storage_options["base_url"] = urlunsplit(
                        url._replace(scheme="https", path="")
                    )
        else:
            args0, argsN = "/", []
        storage_options = {**base_options, **storage_options}
        if "base_url" not in storage_options:
            raise ValueError(
                f"must provide `base_url` storage option for args: {args!r}"
            )
        self._protocol = "webdav"
        super().__init__(args0, *argsN, protocol="webdav", **storage_options)

    @property
    def path(self) -> str:
        # webdav paths don't start at "/"
        return str_remove_prefix(super().path, "/")

    def __str__(self):
        base_url = str_remove_suffix(self.storage_options["base_url"], "/")
        return super().__str__().replace("webdav://", f"webdav+{base_url}", 1)
