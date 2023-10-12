"""
GitHub implementation of UPath
"""

import upath.core


class _GitHubAccessor(upath.core._FSSpecAccessor):
    """
    FSSpecAccessor for GitHub
    """

    def _format_path(self, path: upath.core.UPath) -> str:
        """
        Remove the leading slash from the path
        """
        return path._path.lstrip("/")


class GitHubPath(upath.core.UPath):
    """
    GitHubPath supporting the fsspec.GitHubFileSystem
    """

    _default_accessor = _GitHubAccessor
