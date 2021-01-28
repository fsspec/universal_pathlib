import pathlib
import urllib
import re

from fsspec.registry import get_filesystem_class

from upath.errors import NotDirectoryError


class _FSSpecAccessor:
    def __init__(self, parsed_url, *args, **kwargs):
        self._url = parsed_url
        cls = get_filesystem_class(self._url.scheme)
        url_kwargs = cls._get_kwargs_from_urls(
            urllib.parse.urlunparse(self._url)
        )
        url_kwargs.update(kwargs)
        self._fs = cls(**url_kwargs)

    def argument_upath_self_to_filepath(self, func):
        """if arguments are passed to the wrapped function, and if the first
        argument is a UniversalPath instance, that argument is replaced with
        the UniversalPath's path attribute
        """

        def wrapper(*args, **kwargs):
            args, kwargs = self._format_path(args, kwargs)
            return func(*args, **kwargs)

        return wrapper

    def _format_path(self, args, kwargs):
        """formats the path properly for the filesystem backend."""
        args = list(args)
        first_arg = args.pop(0)
        if not kwargs.get("path"):
            if isinstance(first_arg, UniversalPath):
                first_arg = self._remove_root_slash(first_arg.path)
                args.insert(0, first_arg)
            args = tuple(args)
        else:
            kwargs["path"] = self._remove_root_slash(kwargs["path"])
        return args, kwargs

    def _remove_root_slash(self, s):
        """If the filesystem backend doesn't have a root_marker, strip the
        leading slash of a path
        """
        if not self._fs.root_marker and s.startswith("/"):
            return s[1:]
        else:
            return s

    def __getattribute__(self, item):
        class_attrs = ["_url", "_fs", "__class__"]
        if item in class_attrs:
            return super().__getattribute__(item)

        class_methods = [
            "__init__",
            "__getattribute__",
            "argument_upath_self_to_filepath",
            "_format_path",
            "_remove_root_slash",
        ]
        if item in class_methods:
            return lambda *args, **kwargs: getattr(self.__class__, item)(
                self, *args, **kwargs
            )

        d = object.__getattribute__(self, "__dict__")
        fs = d.get("_fs", None)
        if fs is not None:
            method = getattr(fs, item, None)
            if method:
                return lambda *args, **kwargs: (
                    self.argument_upath_self_to_filepath(method)(
                        *args, **kwargs
                    )
                )  # noqa: E501
            else:
                raise NotImplementedError(
                    f"{fs.protocol} filesystem has not attribute {item}"
                )


class PureUniversalPath(pathlib.PurePath):
    _flavour = pathlib._posix_flavour
    __slots__ = ()


class UniversalPath(pathlib.Path, PureUniversalPath):

    __slots__ = ("_url", "_kwargs", "_closed", "fs")

    not_implemented = [
        "cwd",
        "home",
        "expanduser",
        "group",
        "is_mount",
        "is_symlink",
        "is_socket",
        "is_fifo",
        "is_block_device",
        "is_char_device",
        "lchmod",
        "lstat",
        "owner",
        "readlink",
    ]
    _default_accessor = _FSSpecAccessor

    def _init(self, *args, template=None, **kwargs):
        self._closed = False
        if not kwargs:
            kwargs = dict(**self._kwargs)
        else:
            self._kwargs = dict(**kwargs)
        self._url = kwargs.pop("_url") if kwargs.get("_url") else None

        if not self._root:
            if not self._parts:
                self._root = "/"
            elif self._parts[0] == "/":
                self._root = self._parts.pop(0)
        if getattr(self, "_str", None):
            delattr(self, "_str")
        if template is not None:
            self._accessor = template._accessor
        else:
            self._accessor = self._default_accessor(self._url, *args, **kwargs)
        self.fs = self._accessor._fs

    def __getattribute__(self, item):
        if item == "__class__":
            return super().__getattribute__("__class__")
        if item in getattr(self.__class__, "not_implemented"):
            raise NotImplementedError(f"UniversalPath has no attribute {item}")
        else:
            return super().__getattribute__(item)

    def _format_parsed_parts(self, drv, root, parts):
        if parts:
            join_parts = parts[1:] if parts[0] == "/" else parts
        else:
            join_parts = []
        if drv or root:
            path = drv + root + self._flavour.join(join_parts)
        else:
            path = self._flavour.join(join_parts)
        scheme, netloc = self._url.scheme, self._url.netloc
        scheme = scheme + ":"
        netloc = "//" + netloc if netloc else ""
        formatted = scheme + netloc + path
        return formatted

    @property
    def path(self):
        if self._parts:
            join_parts = (
                self._parts[1:] if self._parts[0] == "/" else self._parts
            )
            path = self._flavour.join(join_parts)
            return self._root + path
        else:
            return "/"

    def open(self, *args, **kwargs):
        return self._accessor.open(self, *args, **kwargs)

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
            sp = self.path
            name = re.sub(f"^({sp}|{sp[1:]})/", "", name)
            yield self._make_child_relpath(name)
            if self._closed:
                self._raise_closed()

    def exists(self):
        """
        Whether this path exists.
        """
        if not getattr(self._accessor, "exists"):
            try:
                self._accessor.stat(self)
            except (FileNotFoundError):
                return False
            return True
        else:
            return self._accessor.exists(self)

    def is_dir(self):
        info = self._accessor.info(self)
        if info["type"] == "directory":
            return True
        return False

    def is_file(self):
        info = self._accessor.info(self)
        if info["type"] == "file":
            return True
        return False

    def glob(self, pattern):
        path = self.joinpath(pattern)
        for name in self._accessor.glob(self, path=path.path):
            sp = self.path
            name = re.sub(f"^({sp}|{sp[1:]})/", "", name)
            name = name.split(self._flavour.sep)
            yield self._make_child(self._parts + name)

    def rename(self, target):
        # can be implimented, but may be tricky
        raise NotImplementedError

    def touch(self, trunicate=True, **kwargs):
        self._accessor.touch(self, trunicate=trunicate, **kwargs)

    def unlink(self, missing_ok=False):
        if not self.exists():
            if not missing_ok:
                raise FileNotFoundError
            else:
                return
        self._accessor.rm(self, recursive=False)

    def rmdir(self, recursive=True):
        """Add warning if directory not empty
        assert is_dir?
        """
        try:
            assert self.is_dir()
        except AssertionError:
            raise NotDirectoryError
        self._accessor.rm(self, recursive=recursive)

    @classmethod
    def _from_parts_init(cls, args, init=False):
        return super()._from_parts(args, init=init)

    def _from_parts(self, args, init=True):
        # We need to call _parse_args on the instance, so as to get the
        # right flavour.
        obj = object.__new__(self.__class__)
        drv, root, parts = self._parse_args(args)
        obj._drv = drv
        obj._root = root
        obj._parts = parts
        if init:
            obj._init(**self._kwargs)
        return obj

    def _from_parsed_parts(self, drv, root, parts, init=True):
        obj = object.__new__(self.__class__)
        obj._drv = drv
        obj._root = root
        obj._parts = parts
        if init:
            obj._init(**self._kwargs)
        return obj
