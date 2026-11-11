from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from upath.core import UPath
from upath.types import JoinablePathLike

if TYPE_CHECKING:
    from typing import Literal

    if sys.version_info >= (3, 11):
        from typing import Unpack
    else:
        from typing_extensions import Unpack

    from upath._chain import FSSpecChainParser
    from upath.types.storage_options import XRootDStorageOptions

__all__ = ["XRootDPath"]


class XRootDPath(UPath):
    __slots__ = ()

    if TYPE_CHECKING:

        def __init__(
            self,
            *args: JoinablePathLike,
            protocol: Literal["root"] | None = ...,
            chain_parser: FSSpecChainParser = ...,
            **storage_options: Unpack[XRootDStorageOptions],
        ) -> None: ...

    def mkdir(
        self, mode: int = 0o777, parents: bool = False, exist_ok: bool = False
    ) -> None:
        if not parents and not exist_ok and self.exists():
            raise FileExistsError(self.path)
        super().mkdir(mode=mode, parents=parents, exist_ok=exist_ok)

    def write_bytes(self, data: bytes) -> int:
        with self.fs.open(self.path, "wb") as f:
            rv = f.write(data)
        return rv
