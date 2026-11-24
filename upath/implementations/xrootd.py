from __future__ import annotations

import sys
from typing import TYPE_CHECKING
from typing import Any

from upath.core import UPath
from upath.types import UNSET_DEFAULT
from upath.types import JoinablePathLike
from upath.types import WritablePathLike

if sys.version_info >= (3, 11):
    from typing import Self
else:
    try:
        from typing_extensions import Self
    except ImportError:  # only needed for resolving annotations at runtime
        pass

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
        self,
        mode: int = 0o777,
        parents: bool = False,
        exist_ok: bool = False,
        *,
        parent_mode: int | None = None,
    ) -> None:
        if not parents and not exist_ok and self.exists():
            raise FileExistsError(self.path)
        super().mkdir(
            mode=mode, parents=parents, exist_ok=exist_ok, parent_mode=parent_mode
        )

    def rmdir(self, recursive: bool = UNSET_DEFAULT) -> None:
        try:
            super().rmdir(recursive=recursive)
        finally:
            self._invalidate_listings()

    def rename(
        self,
        target: WritablePathLike,
        *,
        recursive: bool = UNSET_DEFAULT,
        maxdepth: int | None = UNSET_DEFAULT,
        **kwargs: Any,
    ) -> Self:
        try:
            return super().rename(
                target, recursive=recursive, maxdepth=maxdepth, **kwargs
            )
        finally:
            self._invalidate_listings()

    def _invalidate_listings(self) -> None:
        # fsspec-xrootd keeps the listings of removed or moved directories in
        # its dircache, and its exists() returns True for any cached path
        fs = self.fs
        path = self.path.rstrip("/")
        for key in list(fs.dircache):
            if key == path or key.startswith(path + "/"):
                fs.invalidate_cache(key)
        fs.invalidate_cache(fs._parent(path))

    def write_bytes(self, data: bytes) -> int:
        with self.fs.open(self.path, "wb") as f:
            rv = f.write(data)
        return rv
