"""
GitHub file system implementation
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from collections.abc import Sequence
from typing import TYPE_CHECKING

import upath.core

if TYPE_CHECKING:
    if sys.version_info > (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self


class GitHubPath(upath.core.UPath):
    """
    GitHubPath supporting the fsspec.GitHubFileSystem
    """

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
