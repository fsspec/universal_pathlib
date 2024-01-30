from __future__ import annotations

import sys

import upath.core


class _HDFSAccessor(upath.core._FSSpecAccessor):
    def __init__(self, parsed_url, *args, **kwargs):
        super().__init__(parsed_url, *args, **kwargs)
        self._fs.root_marker = "/"

    def touch(self, path, **kwargs):
        kwargs.pop("truncate", None)
        super().touch(path, **kwargs)

    def mkdir(self, path, create_parents=True, **kwargs):
        pth = self._format_path(path)
        if create_parents:
            return self._fs.makedirs(pth, **kwargs)
        else:
            if not kwargs.get("exist_ok", False) and self._fs.exists(pth):
                raise FileExistsError(pth)
            print(kwargs, self._fs.exists(pth), pth)
            return self._fs.mkdir(pth, create_parents=create_parents, **kwargs)

    def listdir(self, path, **kwargs):
        try:
            yield from super().listdir(path, **kwargs)
        except OSError as err:
            if err.args and err.args[0].startswith(
                "GetFileInfo expects base_dir of selector to be a directory"
            ):
                raise NotADirectoryError(path)
            raise


class HDFSPath(upath.core.UPath):
    _default_accessor = _HDFSAccessor


if sys.version_info >= (3, 12):
    import upath.core312plus

    class HDFSPath(upath.core312plus.UPath):  # noqa
        __slots__ = ()

        def mkdir(self, mode=0o777, parents=False, exist_ok=False):
            if not exist_ok and self.exists():
                raise FileExistsError(str(self))
            super().mkdir(mode=mode, parents=parents, exist_ok=exist_ok)

        def iterdir(self):
            if self.is_file():
                raise NotADirectoryError(str(self))
            yield from super().iterdir()
