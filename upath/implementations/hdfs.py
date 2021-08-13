import upath.core


class _HDFSAccessor(upath.core._FSSpecAccessor):
    def __init__(self, parsed_url, *args, **kwargs):
        super().__init__(parsed_url, *args, **kwargs)
        self._fs.root_marker = "/"

    def transform_args_wrapper(self, func):
        """If arguments are passed to the wrapped function, and if the first
        argument is a UPath instance, that argument is replaced with
        the UPath's path attribute
        """

        def wrapper(*args, **kwargs):
            args, kwargs = self._transform_arg_paths(args, kwargs)
            if "trunicate" in kwargs:
                kwargs.pop("trunicate")
            if func.__name__ == "mkdir":
                args = args[:1]
            return func(*args, **kwargs)

        return wrapper


class HDFSPath(upath.core.UPath):
    _default_accessor = _HDFSAccessor
