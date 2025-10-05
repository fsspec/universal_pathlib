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
    from upath.types.storage_options import SimpleCacheStorageOptions


__all__ = ["SimpleCachePath"]


class SimpleCachePath(UPath):
    __slots__ = ()

    if TYPE_CHECKING:

        def __init__(
            self,
            *args: JoinablePathLike,
            protocol: Literal["simplecache"] | None = ...,
            chain_parser: FSSpecChainParser = ...,
            **storage_options: Unpack[SimpleCacheStorageOptions],
        ) -> None: ...
