from upath.universal_path import _FSSpecAccessor, UniversalPath


class _HDFSAccessor(_FSSpecAccessor):
    def __init__(self, parsed_url, *args, **kwargs):
        super().__init__(parsed_url, *args, **kwargs)
        self._fs.root_marker = "/"

    def transform_args_wrapper(self, func):
        """if arguments are passed to the wrapped function, and if the first
        argument is a UniversalPath instance, that argument is replaced with
        the UniversalPath's path attribute
        """

        def wrapper(*args, **kwargs):
            args, kwargs = self._transform_arg_paths(args, kwargs)
            if "trunicate" in kwargs:
                kwargs.pop("trunicate")
            if func.__name__ == "mkdir":
                args = args[:1]
            return func(*args, **kwargs)

        return wrapper


class HDFSPath(UniversalPath):
    _default_accessor = _HDFSAccessor
