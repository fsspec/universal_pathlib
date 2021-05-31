import os
import pathlib
import urllib

from fsspec.registry import known_implementations, registry

from upath.registry import _registry


class UPath(pathlib.Path):
    def __new__(cls, *args, **kwargs):
        if cls is UPath:
            args_list = list(args)
            url = args_list.pop(0)
            parsed_url = urllib.parse.urlparse(url)
            for key in ["scheme", "netloc"]:
                val = kwargs.get(key)
                if val:
                    parsed_url = parsed_url._replace(**{key: val})
            # treat as local filesystem, return PosixPath or WindowsPath
            impls = list(registry) + list(known_implementations.keys())
            if not parsed_url.scheme or parsed_url.scheme not in impls:
                cls = (
                    pathlib.WindowsPath
                    if os.name == "nt"
                    else pathlib.PosixPath
                )
                self = cls._from_parts(args, init=False)
                if not self._flavour.is_supported:
                    raise NotImplementedError(
                        "cannot instantiate %r on your system" % (cls.__name__,)
                    )
                self._init()
            else:
                cls = _registry[parsed_url.scheme]
                kwargs["_url"] = parsed_url
                args_list.insert(0, parsed_url.path)
                args = tuple(args_list)
                self = cls._from_parts_init(args, init=False)
                self._init(*args, **kwargs)
        return self
