from __future__ import annotations

import sys
from types import MappingProxyType
from typing import TYPE_CHECKING

from upath.core import UPath
from upath.types import JoinablePathLike

if TYPE_CHECKING:
    from collections.abc import Iterator
    from collections.abc import Mapping
    from typing import Any
    from typing import Literal

    if sys.version_info >= (3, 11):
        from typing import Self
        from typing import Unpack
    else:
        from typing_extensions import Self
        from typing_extensions import Unpack

    from fsspec import AbstractFileSystem

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

    @classmethod
    def _fs_factory(
        cls,
        urlpath: str,
        protocol: str,
        storage_options: Mapping[str, Any],
    ) -> AbstractFileSystem:
        so = dict(storage_options)
        so.pop("fo", None)
        return super()._fs_factory(
            urlpath,
            protocol,
            so,
        )

    @property
    def storage_options(self) -> Mapping[str, Any]:
        so = self._storage_options.copy()
        so.pop("fo", None)
        return MappingProxyType(so)

    def iterdir(self) -> Iterator[Self]:
        if self.is_file():
            raise NotADirectoryError(str(self))
        yield from super().iterdir()
