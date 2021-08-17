import upath.core


class _MemoryAccessor(upath.core._FSSpecAccessor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fs.root_marker = ""

    def _format_path(self, s):
        """If the filesystem backend doesn't have a root_marker, strip the
        leading slash of a path
        """
        return s


class MemoryPath(upath.core.UPath):
    _default_accessor = _MemoryAccessor

    def iterdir(self):
        """Iterate over the files in this directory.  Does not yield any
        result for the special paths '.' and '..'.
        """
        if self._closed:
            self._raise_closed()
        for name in self._accessor.listdir(self):
            # fsspec returns dictionaries
            if isinstance(name, dict):
                name = name.get("name")
            if name in {".", ".."}:
                # Yielding a path object for these makes little sense
                continue
            # only want the path name with iterdir
            name = name.rstrip("/")
            name = self._sub_path(name)
            yield self._make_child_relpath(name)
            if self._closed:
                self._raise_closed()
