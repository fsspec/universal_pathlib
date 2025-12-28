"""
GitHub file system implementation
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from typing import TYPE_CHECKING

from upath.core import UnsupportedOperation
from upath.core import UPath
from upath.types import JoinablePathLike

if TYPE_CHECKING:
    from typing import Literal

    if sys.version_info >= (3, 11):
        from typing import Unpack
    else:
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

    @property
    def parts(self) -> Sequence[str]:
        parts = super().parts
        if parts and parts[0] == "/":
            return parts[1:]
        else:
            return parts

    def touch(self, mode: int = 0o666, exist_ok: bool = True) -> None:
        raise UnsupportedOperation

    def mkdir(
        self,
        mode: int = 0o777,
        parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
        raise UnsupportedOperation

    def unlink(self, missing_ok: bool = False) -> None:
        raise UnsupportedOperation

    def write_bytes(self, data: bytes) -> int:
        raise UnsupportedOperation

    def write_text(
        self,
        data: str,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> int:
        raise UnsupportedOperation("GitHubPath does not support writing")
