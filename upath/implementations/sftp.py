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
    from upath.types.storage_options import SFTPStorageOptions

__all__ = ["SFTPPath"]


class SFTPPath(UPath):
    __slots__ = ()

    if TYPE_CHECKING:

        def __init__(
            self,
            *args: JoinablePathLike,
            protocol: Literal["sftp"] | None = ...,
            chain_parser: FSSpecChainParser = ...,
            **storage_options: Unpack[SFTPStorageOptions],
        ) -> None: ...

    @property
    def path(self) -> str:
        path = super().path
        if len(path) > 1:
            return path.removesuffix("/")
        return path

    def __str__(self) -> str:
        path_str = super().__str__()
        if path_str.startswith(("ssh:///", "sftp:///")):
            return path_str.removesuffix("/")
        return path_str

    def iterdir(self) -> Iterator[Self]:
        if not self.is_dir():
            raise NotADirectoryError(str(self))
        else:
            return super().iterdir()
