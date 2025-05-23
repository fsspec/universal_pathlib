from __future__ import annotations

from upath.core import UPath

__all__ = ["MemoryPath"]


class MemoryPath(UPath):
    def iterdir(self):
        if not self.is_dir():
            raise NotADirectoryError(str(self))
        yield from super().iterdir()

    @property
    def path(self):
        path = super().path
        return "/" if path == "." else path

    def __str__(self):
        s = super().__str__()
        if s.startswith("memory:///"):
            s = s.replace("memory:///", "memory://", 1)
        return s
