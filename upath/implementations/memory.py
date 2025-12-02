from __future__ import annotations

import sys
from collections.abc import Iterator
from typing import TYPE_CHECKING

from upath.core import UPath
from upath.types import JoinablePathLike

if TYPE_CHECKING:
    from typing import Literal

    if sys.version_info >= (3, 11):
        from typing import Self
        from typing import Unpack
    else:
        from typing_extensions import Self
        from typing_extensions import Unpack

    from upath._chain import FSSpecChainParser
    from upath.types.storage_options import MemoryStorageOptions

__all__ = ["MemoryPath"]


class MemoryPath(UPath):
    __slots__ = ()

    if TYPE_CHECKING:

        def __init__(
            self,
            *args: JoinablePathLike,
            protocol: Literal["memory"] | None = ...,
            chain_parser: FSSpecChainParser = ...,
            **storage_options: Unpack[MemoryStorageOptions],
        ) -> None: ...

    def iterdir(self) -> Iterator[Self]:
        if not self.is_dir():
            raise NotADirectoryError(str(self))
        yield from super().iterdir()

    @property
    def path(self) -> str:
        path = super().path
        return "/" if path in {"", "."} else path

    def is_absolute(self) -> bool:
        if self._relative_base is None and self.__vfspath__() == "/":
            return True
        return super().is_absolute()

    def __str__(self) -> str:
        s = super().__str__()
        if s.startswith("memory:///"):
            s = s.replace("memory:///", "memory://", 1)
        return s
