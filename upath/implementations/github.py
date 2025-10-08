"""
GitHub file system implementation
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from collections.abc import Sequence
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
    from upath.types.storage_options import GitHubStorageOptions

__all__ = ["GitHubPath"]


class GitHubPath(UPath):
    """
    GitHubPath supporting the fsspec.GitHubFileSystem
    """

    __slots__ = ()

    if TYPE_CHECKING:

        def __init__(
            self,
            *args: JoinablePathLike,
            protocol: Literal["github"] | None = ...,
            chain_parser: FSSpecChainParser = ...,
            **storage_options: Unpack[GitHubStorageOptions],
        ) -> None: ...

    @property
    def path(self) -> str:
        pth = super().path
        if pth == ".":
            return ""
        return pth

    def iterdir(self) -> Iterator[Self]:
        if self.is_file():
            raise NotADirectoryError(str(self))
        yield from super().iterdir()

    @property
    def parts(self) -> Sequence[str]:
        parts = super().parts
        if parts and parts[0] == "/":
            return parts[1:]
        else:
            return parts
