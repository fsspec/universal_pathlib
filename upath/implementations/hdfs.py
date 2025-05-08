from __future__ import annotations

from upath.core import UPath

__all__ = ["HDFSPath"]


class HDFSPath(UPath):
    __slots__ = ()

    def mkdir(self, mode=0o777, parents=False, exist_ok=False):
        if not exist_ok and self.exists():
            raise FileExistsError(str(self))
        super().mkdir(mode=mode, parents=parents, exist_ok=exist_ok)

    def iterdir(self):
        if self.is_file():
            raise NotADirectoryError(str(self))
        yield from super().iterdir()
