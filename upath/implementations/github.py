import upath.core


class _GithubAccessor(upath.core._FSSpecAccessor):
    def glob(self, _path, path_pattern, **kwargs):
        return self._fs.glob(
            self._format_path(path_pattern).lstrip("/"), **kwargs
        )

    def exists(self, path, **kwargs):
        return self._fs.exists(self._format_path(path).lstrip("/"), **kwargs)

    def info(self, path, **kwargs):
        return self._fs.info(self._format_path(path).lstrip("/"), **kwargs)


class GithubPath(upath.core.UPath):
    _default_accessor = _GithubAccessor
