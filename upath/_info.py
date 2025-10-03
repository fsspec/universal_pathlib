from __future__ import annotations

from typing import TYPE_CHECKING

from upath.types import PathInfo

if TYPE_CHECKING:
    from upath import UPath


__all__ = [
    "UPathInfo",
]


class UPathInfo(PathInfo):
    """Path info for UPath objects."""

    def __init__(self, path: UPath) -> None:
        self._path = path.path
        self._fs = path.fs

    def exists(self, *, follow_symlinks=True) -> bool:
        return self._fs.exists(self._path)

    def is_dir(self, *, follow_symlinks=True) -> bool:
        return self._fs.isdir(self._path)

    def is_file(self, *, follow_symlinks=True) -> bool:
        return self._fs.isfile(self._path)

    def is_symlink(self) -> bool:
        return False
