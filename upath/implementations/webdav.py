from __future__ import annotations

import sys
from typing import Any
from urllib.parse import ParseResult
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

import upath.core


class _WebdavAccessor(upath.core._FSSpecAccessor):
    def __init__(self, parsed_url: ParseResult, **kwargs):
        from webdav4.fsspec import WebdavFileSystem

        parsed_url = parsed_url._replace(scheme=parsed_url.scheme[7:], path="")
        base_url = urlunsplit(parsed_url)
        self._fs = WebdavFileSystem(base_url=base_url, **kwargs)

    def listdir(self, path, **kwargs):
        base_url = urlunsplit(path._url._replace(path=""))
        for file_info in self._fs.listdir(
            self._format_path(path).lstrip("/"), **kwargs
        ):
            yield {
                **file_info,
                "name": f"{base_url}/{file_info['name']}",
            }

    def glob(self, path, path_pattern, **kwargs):
        base_url = urlunsplit(path._url._replace(path=""))
        for file_path in self._fs.glob(
            self._format_path(path_pattern).lstrip("/"), **kwargs
        ):
            yield f"{base_url}/{file_path}"


class WebdavPath(upath.core.UPath):
    _default_accessor = _WebdavAccessor

    def _sub_path(self, name):
        """fsspec returns path as `scheme://netloc/<path>` with listdir
        and glob, so we potentially need to sub the whole string
        """
        sp = self.path
        complete_address = self._format_parsed_parts(
            None, None, [sp], url=self._url, **self._kwargs
        )

        if name.startswith(complete_address):
            name = name[len(complete_address) :]  # noqa: E203
        name = name.strip("/")

        return name

    @property
    def protocol(self) -> str:
        if self._url is None:
            raise RuntimeError(str(self))
        return self._url.scheme.split("+")[0]

    @property
    def storage_options(self) -> dict[str, Any]:
        if self._url is None:
            raise RuntimeError(str(self))
        sopts = super().storage_options
        http_protocol = self._url.scheme.split("+")[1]
        assert http_protocol in {"http", "https"}
        base_url = urlunsplit(self._url._replace(scheme=http_protocol, path=""))
        sopts["base_url"] = base_url
        return sopts


if sys.version_info >= (3, 12):
    import upath.core312plus

    class WebdavPath(upath.core312plus.UPath):  # noqa
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
                args0, argsN = "/", ()
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
            return super().path.removeprefix("/")

        def __str__(self):
            base_url = self.storage_options["base_url"].removesuffix("/")
            return super().__str__().replace("webdav://", f"webdav+{base_url}", 1)
