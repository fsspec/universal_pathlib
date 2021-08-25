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
                    new_url = self._url.replace(path=kwargs["path"])
                    unparsed = urllib.urlunparse(new_url)
                    kwargs["path"] = unparsed
            return func(*args, **kwargs)

        return wrapper


class HTTPPath(upath.core.UPath):
    _default_accessor = _HTTPAccessor
