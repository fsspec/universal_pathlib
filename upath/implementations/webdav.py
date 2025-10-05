from __future__ import annotations

import sys
from collections.abc import Mapping
from collections.abc import Sequence
from typing import TYPE_CHECKING
from typing import Any
from urllib.parse import urlsplit

from fsspec.registry import known_implementations
from fsspec.registry import register_implementation

from upath.core import UPath
from upath.types import JoinablePathLike

if TYPE_CHECKING:
    from typing import Literal

    if sys.version_info >= (3, 11):
        from typing import Unpack
    else:
        from typing_extensions import Unpack

    from upath._chain import FSSpecChainParser
    from upath.types.storage_options import WebdavStorageOptions

__all__ = ["WebdavPath"]

# webdav was only registered in fsspec>=2022.5.0
if "webdav" not in known_implementations:
    import webdav4.fsspec

    register_implementation("webdav", webdav4.fsspec.WebdavFileSystem)


class WebdavPath(UPath):
    __slots__ = ()

    if TYPE_CHECKING:

        def __init__(
            self,
            *args: JoinablePathLike,
            protocol: Literal["webdav+http", "webdav+https"] | None = ...,
            chain_parser: FSSpecChainParser = ...,
            **storage_options: Unpack[WebdavStorageOptions],
        ) -> None: ...

    @classmethod
    def _transform_init_args(
        cls,
        args: tuple[JoinablePathLike, ...],
        protocol: str,
        storage_options: dict[str, Any],
    ) -> tuple[tuple[JoinablePathLike, ...], str, dict[str, Any]]:
        if not args:
            args = ("/",)
        elif args and protocol in {"webdav+http", "webdav+https"}:
            args0, *argsN = args
            url = urlsplit(str(args0))
            base = url._replace(scheme=protocol.split("+")[1], path="").geturl()
            args0 = url._replace(scheme="", netloc="").geturl() or "/"
            storage_options["base_url"] = base
            args = (args0, *argsN)
        if "base_url" not in storage_options:
            raise ValueError(
                f"must provide `base_url` storage option for args: {args!r}"
            )
        return super()._transform_init_args(args, "webdav", storage_options)

    @classmethod
    def _parse_storage_options(
        cls,
        urlpath: str,
        protocol: str,
        storage_options: Mapping[str, Any],
    ) -> dict[str, Any]:
        so = dict(storage_options)
        if urlpath.startswith(("webdav+http:", "webdav+https:")):
            url = urlsplit(str(urlpath))
            base = url._replace(scheme=url.scheme.split("+")[1], path="").geturl()
            urlpath = url._replace(scheme="", netloc="").geturl() or "/"
            so.setdefault("base_url", base)
        return super()._parse_storage_options(urlpath, "webdav", so)

    @property
    def parts(self) -> Sequence[str]:
        parts = super().parts
        if parts and parts[0] == "/":
            return parts[1:]
        else:
            return parts
