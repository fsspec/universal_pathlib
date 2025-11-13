from __future__ import annotations

import stat
import sys
import warnings
from typing import TYPE_CHECKING

from upath._stat import UPathStatResult
from upath.core import UPath
from upath.types import JoinablePathLike
from upath.types import StatResultType

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Literal

    if sys.version_info >= (3, 11):
        from typing import Self
        from typing import Unpack
    else:
        from typing_extensions import Self
        from typing_extensions import Unpack

    from upath._chain import FSSpecChainParser
    from upath.types.storage_options import TarStorageOptions


__all__ = ["TarPath"]


class TarPath(UPath):
    __slots__ = ()

    if TYPE_CHECKING:

        def __init__(
            self,
            *args: JoinablePathLike,
            protocol: Literal["zip"] | None = ...,
            chain_parser: FSSpecChainParser = ...,
            **storage_options: Unpack[TarStorageOptions],
        ) -> None: ...

    def stat(
        self,
        *,
        follow_symlinks: bool = True,
    ) -> StatResultType:
        if not follow_symlinks:
            warnings.warn(
                f"{type(self).__name__}.stat(follow_symlinks=False):"
                " is currently ignored.",
                UserWarning,
                stacklevel=2,
            )
        info = self.fs.info(self.path).copy()
        # convert mode
        if info["type"] == "directory":
            info["mode"] = stat.S_IFDIR
        elif info["type"] == "file":
            info["mode"] = stat.S_IFREG
        return UPathStatResult.from_info(info)

    def iterdir(self) -> Iterator[Self]:
        if self.is_file():
            raise NotADirectoryError(str(self))
        it = iter(super().iterdir())
        p0 = next(it)
        if p0.name != "":
            yield p0
        yield from it
