from __future__ import annotations

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
            return self._fs.mkdir(pth, create_parents=create_parents, **kwargs)


class HDFSPath(upath.core.UPath):
    _default_accessor = _HDFSAccessor
