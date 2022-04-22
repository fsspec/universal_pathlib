import urllib

import upath.core


class _HTTPAccessor(upath.core._FSSpecAccessor):
    def __init__(self, parsed_url, *args, **kwargs):
        super().__init__(parsed_url, *args, **kwargs)

    def transform_args_wrapper(self, func):
        """if arguments are passed to the wrapped function, and if the first
        argument is a UPath instance, that argument is replaced with
        the UPath's path attribute
        """

        def wrapper(*args, **kwargs):
            if args:
                args = list(args)
                first_arg = args.pop(0)
                if not kwargs.get("path"):
                    if isinstance(first_arg, upath.core.UPath):
                        first_arg = str(first_arg)
                        args.insert(0, first_arg)
                    args = tuple(args)
                else:
                    new_url = self._url._replace(path=kwargs["path"])
                    unparsed = urllib.parse.urlunparse(new_url)
                    kwargs["path"] = unparsed
            return func(*args, **kwargs)

        return wrapper


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
        info = self._accessor.info(self)
        if (
            info["type"] == "directory"
            or next(self.iterdir(), None) is not None
        ):
            return "directory"
        return "file"

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
