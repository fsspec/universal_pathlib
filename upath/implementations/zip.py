from __future__ import annotations

import re
from urllib.parse import ParseResult

import upath.core
from fsspec.implementations.zip import ZipFileSystem


class _ZipAccessor(upath.core._FSSpecAccessor):
    def __init__(self, parsed_url: ParseResult, **kwargs):

        self._fs = ZipFileSystem(f"{parsed_url.netloc}/{parsed_url.path}")

    def _format_path(self, path: ZipPath):
        ret = re.sub(rf"^{path._url.path}", "", path.path.lstrip("/"))

        if not (ret):
            return "/"

        return ret.lstrip("/")


class ZipPath(upath.core.UPath):
    _default_accessor = _ZipAccessor

    @classmethod
    def _from_parts(cls, args, url=None, **kwargs):
        url_parts = url.path.split("/")
        zip_ext_index = (
            next(
                (
                    url_parts.index(part)
                    for part in url_parts
                    if part.split(".")[-1] == "zip"
                )
            )
            + 1
        )

        path = "/".join(url_parts[:zip_ext_index]).lstrip("/")

        url = url._replace(path=path)

        return super()._from_parts(args, url, **kwargs)

    def iterdir(self):
        for name in self._accessor.listdir(self):
            # fsspec returns dictionaries
            if isinstance(name, dict):
                name = name.get("name")
            if name in {".", ".."}:
                # Yielding a path object for these makes little sense
                continue
            # only want the path name with iterdir
            name = name.rstrip("/").split("/")[-1]
            name = self._sub_path(name)
            yield self._make_child_relpath(name)

    def mkdir(
        self, mode: int = ..., parents: bool = ..., exist_ok: bool = ...
    ) -> None:
        raise NotImplementedError
