import upath.core


class _HTTPAccessor(upath.core._FSSpecAccessor):
    def __init__(self, parsed_url, *args, **kwargs):
        super().__init__(parsed_url, *args, **kwargs)

    def _format_path(self, path):
        return str(path)


class HTTPPath(upath.core.UPath):
    _default_accessor = _HTTPAccessor

    def is_dir(self):
        try:
            return self._path_type() == "directory"
        except FileNotFoundError:
            return False

    def is_file(self):
        try:
            return self._path_type() == "file"
        except FileNotFoundError:
            return False

    def _path_type(self):
        try:
            next(self.iterdir())
        except (StopIteration, NotADirectoryError):
            return "file"
        else:
            return "directory"

    def _sub_path(self, name):
        """
        `fsspec` returns the full path as `scheme://netloc/<path>` with
        `listdir` and `glob`. However, in `iterdir` and `glob` we only want the
        relative path to `self`.
        """
        complete_address = self._format_parsed_parts(None, None, [self.path])

        if name.startswith(complete_address):
            name = name[len(complete_address) :]  # noqa: E203
        name = name.strip("/")

        return name
