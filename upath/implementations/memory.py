from __future__ import annotations

import sys
from collections.abc import Iterator
from typing import TYPE_CHECKING

from upath.core import UPath

if TYPE_CHECKING:
    if sys.version_info > (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self

__all__ = ["MemoryPath"]


class MemoryPath(UPath):
    def iterdir(self) -> Iterator[Self]:
        if not self.is_dir():
            raise NotADirectoryError(str(self))
        yield from super().iterdir()

    @property
    def path(self) -> str:
        path = super().path
        return "/" if path == "." else path

    def __str__(self) -> str:
        s = super().__str__()
        if s.startswith("memory:///"):
            s = s.replace("memory:///", "memory://", 1)
        return s
