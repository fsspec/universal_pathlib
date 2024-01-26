from __future__ import annotations

import sys
from typing import Any
from urllib.parse import SplitResult

import upath.core
from upath.core import PT


class _MemoryAccessor(upath.core._FSSpecAccessor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fs.root_marker = ""


class MemoryPath(upath.core.UPath):
    _default_accessor = _MemoryAccessor

    def iterdir(self):
        """Iterate over the files in this directory.  Does not yield any
        result for the special paths '.' and '..'.
        """
        for name in self._accessor.listdir(self):
            # fsspec returns dictionaries
            if isinstance(name, dict):
                name = name.get("name")
            if name in {".", ".."}:
                # Yielding a path object for these makes little sense
                continue
            # only want the path name with iterdir
            name = name.rstrip("/")
            name = self._sub_path(name)
            yield self._make_child_relpath(name)

    @classmethod
    def _from_parts(cls, args, url=None, **kwargs):
        if url and url.netloc:
            if args:
                if args[0].startswith("/"):
                    args[0] = args[0][1:]
                args[0:1] = [f"/{url.netloc}/{args[0]}"]
            else:
                args[:] = f"/{url.netloc}"
            url = url._replace(netloc="")
        return super()._from_parts(args, url=url, **kwargs)

    @classmethod
    def _format_parsed_parts(
        cls: type[PT],
        drv: str,
        root: str,
        parts: list[str],
        url: SplitResult | None = None,
        **kwargs: Any,
    ) -> str:
        s = super()._format_parsed_parts(drv, root, parts, url=url, **kwargs)
        if s.startswith("memory:///"):
            s = s.replace("memory:///", "memory://", 1)
        return s


if sys.version_info >= (3, 12):

    class MemoryPath(upath.core.UPath):  # noqa
        def iterdir(self):
            if not self.is_dir():
                raise NotADirectoryError(str(self))
            yield from super().iterdir()

        @property
        def path(self):
            path = super().path
            return "/" if path == "." else path
