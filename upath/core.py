import os
import pathlib
import re
import urllib
from abc import ABCMeta

from fsspec.registry import (
    get_filesystem_class,
    known_implementations,
    registry,
)
from fsspec.utils import stringify_path

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

    def transform_args_wrapper(self, func):
        """Modifies the arguments that get passed to the filesystem so that
        the UPath instance gets stripped as the first argument. If a
        path keyword argument is not given, then `UPath.path` is
        formatted for the filesystem and inserted as the first argument.
        If it is, then the path keyword argument is formatted properly for
        the filesystem.
        """

        def wrapper(*args, **kwargs):
            args, kwargs = self._transform_arg_paths(args, kwargs)
            return func(*args, **kwargs)

        return wrapper

    def _transform_arg_paths(self, args, kwargs):
        """Formats the path properly for the filesystem backend."""
        args = list(args)
        first_arg = args.pop(0)
        if not kwargs.get("path"):
            if isinstance(first_arg, UPath):
                first_arg = self._format_path(first_arg.path)
                args.insert(0, first_arg)
            args = tuple(args)
        else:
            kwargs["path"] = self._format_path(kwargs["path"])
        return args, kwargs

    def _format_path(self, s):
        """Placeholder method for subclassed filesystems"""
        return s

    def __getattribute__(self, item):
        class_attrs = ["_url", "_fs", "__class__"]
        if item in class_attrs:
            return super().__getattribute__(item)

        class_methods = [
            "__init__",
            "__getattribute__",
            "transform_args_wrapper",
            "_transform_arg_paths",
            "_format_path",
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
                    self.transform_args_wrapper(method)(*args, **kwargs)
                )  # noqa: E501
            else:
                raise NotImplementedError(
                    f"{fs.protocol} filesystem has no attribute {item}"
                )


class PureUPath(pathlib.PurePath):
    _flavour = pathlib._posix_flavour
    __slots__ = ()


class UPathMeta(ABCMeta):
    def __instancecheck__(cls, instance):
        return isinstance(instance, pathlib.Path)

    def __subclasscheck__(cls, subclass):
        return issubclass(subclass, pathlib.Path)


class UPath(pathlib.Path, PureUPath, metaclass=UPathMeta):

    __slots__ = ("_url", "_kwargs", "_closed", "_accessor")

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

    def __new__(cls, *args, **kwargs):
        if issubclass(cls, UPath):
            args_list = list(args)
            url = args_list.pop(0)
            url = stringify_path(url)
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
                self = cls._from_parts(args)
                if not self._flavour.is_supported:
                    raise NotImplementedError(
                        "cannot instantiate %r on your system" % (cls.__name__,)
                    )
            else:
                import upath.registry

                cls = upath.registry._registry[parsed_url.scheme]
                kwargs["_url"] = parsed_url
                args_list.insert(0, parsed_url.path)
                args = tuple(args_list)
                self = cls._from_parts(args, **kwargs)
        else:
            self = super().__new__(*args, **kwargs)
        return self

    def __getattr__(self, item):
        if item == "_accessor":
            # cache the _accessor attribute on first access
            kw = self._kwargs.copy()
            kw.pop("_url", None)
            self._accessor = _accessor = self._default_accessor(self._url, **kw)
            return _accessor
        else:
            raise AttributeError(item)

    def __getattribute__(self, item):
        if item == "__class__":
            return super().__getattribute__("__class__")
        if item in getattr(self.__class__, "not_implemented"):
            raise NotImplementedError(f"UPath has no attribute {item}")
        else:
            return super().__getattribute__(item)

    def _make_child(self, args):
        drv, root, parts = self._parse_args(args, **self._kwargs)
        drv, root, parts = self._flavour.join_parsed_parts(
            self._drv, self._root, self._parts, drv, root, parts
        )
        return self._from_parsed_parts(drv, root, parts, **self._kwargs)

    def _make_child_relpath(self, part):
        # This is an optimization used for dir walking.  `part` must be
        # a single part relative to this path.
        parts = self._parts + [part]
        return self._from_parsed_parts(
            self._drv, self._root, parts, **self._kwargs
        )

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

    @property
    def parent(self):
        """The logical parent of the path."""
        drv = self._drv
        root = self._root
        parts = self._parts
        if len(parts) == 1 and (drv or root):
            return self
        return self._from_parsed_parts(drv, root, parts[:-1], **self._kwargs)

    def stat(self):
        return self._accessor.stat(self)

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
            name = self._sub_path(name)
            yield self._make_child_relpath(name)
            if self._closed:
                self._raise_closed()

    def glob(self, pattern):
        path = self.joinpath(pattern)
        for name in self._accessor.glob(self, path=path.path):
            name = self._sub_path(name)
            name = name.split(self._flavour.sep)
            yield self._make_child(name)

    def _sub_path(self, name):
        # only want the path name with iterdir
        sp = self.path
        return re.sub(f"^({sp}|{sp[1:]})/", "", name)

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

    def chmod(self, mod):
        raise NotImplementedError

    def rename(self, target):
        # can be implemented, but may be tricky
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
    def _parse_args(cls, args, **kwargs):
        return super(UPath, cls)._parse_args(args)

    @classmethod
    def _from_parts(cls, args, **kwargs):
        obj = object.__new__(cls)
        drv, root, parts = obj._parse_args(args, **kwargs)
        obj._drv = drv
        obj._parts = parts
        obj._closed = False
        obj._kwargs = kwargs.copy()
        obj._url = kwargs.pop("_url", None) or None

        if not root:
            if not parts:
                root = "/"
            elif parts[0] == "/":
                root = parts.pop(0)
        obj._root = root

        return obj

    @classmethod
    def _from_parsed_parts(cls, drv, root, parts, **kwargs):
        obj = object.__new__(cls)
        obj._drv = drv
        obj._parts = parts
        obj._closed = False
        obj._kwargs = kwargs.copy()
        obj._url = kwargs.pop("_url", None) or None

        if not root:
            if not parts:
                root = "/"
            elif parts[0] == "/":
                root = parts.pop(0)
        obj._root = root

        return obj

    @property
    def fs(self):
        return self._accessor._fs

    def __truediv__(self, key):
        # Add `/` root if not present
        if len(self._parts) == 0:
            key = f"{self._root}{key}"

        # Adapted from `PurePath._make_child`
        drv, root, parts = self._parse_args((key,))
        drv, root, parts = self._flavour.join_parsed_parts(
            self._drv, self._root, self._parts, drv, root, parts
        )

        kwargs = self._kwargs.copy()
        kwargs.pop("_url")

        # Create a new object
        out = self.__class__(
            self._format_parsed_parts(drv, root, parts),
            **kwargs,
        )
        return out

    def __setstate__(self, state):
        kwargs = state["_kwargs"].copy()
        kwargs["_url"] = self._url
        self._kwargs = kwargs

    def __reduce__(self):
        kwargs = self._kwargs.copy()
        kwargs.pop("_url", None)

        return (
            self.__class__,
            (self._format_parsed_parts(self._drv, self._root, self._parts),),
            {"_kwargs": kwargs},
        )
