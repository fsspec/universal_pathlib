import upath.core


class _HDFSAccessor(upath.core._FSSpecAccessor):
    def __init__(self, parsed_url, *args, **kwargs):
        super().__init__(parsed_url, *args, **kwargs)
        self._fs.root_marker = "/"

    def touch(self, **kwargs):
        kwargs.pop("trunicate", None)
        super().touch(self, **kwargs)


class HDFSPath(upath.core.UPath):
    _default_accessor = _HDFSAccessor
