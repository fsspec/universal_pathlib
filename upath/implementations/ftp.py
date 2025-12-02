from __future__ import annotations

import sys
from collections.abc import Iterator
from ftplib import error_perm as FTPPermanentError  # nosec B402
from typing import TYPE_CHECKING

from upath.core import UPath
from upath.types import UNSET_DEFAULT
from upath.types import JoinablePathLike

if TYPE_CHECKING:
    from typing import Any
    from typing import Literal

    if sys.version_info >= (3, 11):
        from typing import Self
        from typing import Unpack
    else:
        from typing_extensions import Self
        from typing_extensions import Unpack

    from upath._chain import FSSpecChainParser
    from upath.types import WritablePathLike
    from upath.types.storage_options import FTPStorageOptions

__all__ = ["FTPPath"]


class FTPPath(UPath):
    __slots__ = ()

    if TYPE_CHECKING:

        def __init__(
            self,
            *args: JoinablePathLike,
            protocol: Literal["ftp"] | None = ...,
            chain_parser: FSSpecChainParser = ...,
            **storage_options: Unpack[FTPStorageOptions],
        ) -> None: ...

    def mkdir(
        self,
        mode: int = 0o777,
        parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
        try:
            return super().mkdir(mode, parents, exist_ok)
        except FTPPermanentError as e:
            if e.args[0].startswith("550") and exist_ok:
                return
            raise FileExistsError(str(self)) from e

    def iterdir(self) -> Iterator[Self]:
        if not self.is_dir():
            raise NotADirectoryError(str(self))
        else:
            return super().iterdir()

    def rename(
        self,
        target: WritablePathLike,
        *,  # note: non-standard compared to pathlib
        recursive: bool = UNSET_DEFAULT,
        maxdepth: int | None = UNSET_DEFAULT,
        **kwargs: Any,
    ) -> Self:
        t = super().rename(target, recursive=recursive, maxdepth=maxdepth, **kwargs)
        self_dir = self.parent.path
        t.fs.invalidate_cache(self_dir)
        self.fs.invalidate_cache(self_dir)
        return t
