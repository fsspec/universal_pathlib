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

__all__ = ["HDFSPath"]


class HDFSPath(UPath):
    __slots__ = ()

    def mkdir(
        self, mode: int = 0o777, parents: bool = False, exist_ok: bool = False
    ) -> None:
        if not exist_ok and self.exists():
            raise FileExistsError(str(self))
        super().mkdir(mode=mode, parents=parents, exist_ok=exist_ok)

    def iterdir(self) -> Iterator[Self]:
        if self.is_file():
            raise NotADirectoryError(str(self))
        yield from super().iterdir()
