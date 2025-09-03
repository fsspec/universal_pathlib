"""
GitHub file system implementation
"""

from collections.abc import Sequence

import upath.core


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

    def iterdir(self):
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
