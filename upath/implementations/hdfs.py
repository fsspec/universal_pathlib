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
    from upath.types.storage_options import HDFSStorageOptions

__all__ = ["HDFSPath"]


class HDFSPath(UPath):
    __slots__ = ()

    if TYPE_CHECKING:

        def __init__(
            self,
            *args: JoinablePathLike,
            protocol: Literal["hdfs"] | None = ...,
            chain_parser: FSSpecChainParser = ...,
            **storage_options: Unpack[HDFSStorageOptions],
        ) -> None: ...

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
