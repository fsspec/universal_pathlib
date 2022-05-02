import pathlib
import re
import sys
from typing import Union
import urllib
from urllib.parse import ParseResult

from fsspec.registry import (
    get_filesystem_class,
    known_implementations,
    registry,
)
from fsspec.utils import stringify_path

from upath.errors import NotDirectoryError


class _FSSpecAccessor:
    __slots__ = ("_fs",)

    def __init__(self, parsed_url: ParseResult, **kwargs):
        cls = get_filesystem_class(parsed_url.scheme)
        url_kwargs = cls._get_kwargs_from_urls(
            urllib.parse.urlunparse(parsed_url)
        )
        url_kwargs.update(kwargs)
        self._fs = cls(**url_kwargs)

    def _format_path(self, path: "UPath") -> str:
        return path.path

    def open(self, path, mode='r', *args, **kwargs):
        return self._fs.open(self._format_path(path), mode, *args, **kwargs)

    def stat(self, path, **kwargs):
        return self._fs.stat(self._format_path(path), **kwargs)

    def listdir(self, path, **kwargs):
        return self._fs.listdir(self._format_path(path), **kwargs)

    def glob(self, _path, path_pattern, **kwargs):
        return self._fs.glob(self._format_path(path_pattern), **kwargs)

    def exists(self, path, **kwargs):
        return self._fs.exists(self._format_path(path), **kwargs)

    def info(self, path, **kwargs):
        return self._fs.info(self._format_path(path), **kwargs)

    def rm(self, path, recursive, **kwargs):
        return self._fs.rm(
            self._format_path(path), recursive=recursive, **kwargs
        )

    def mkdir(self, path, create_parents=True, **kwargs):
        return self._fs.mkdir(
            self._format_path(path), create_parents=create_parents, **kwargs
        )

    def touch(self, path, **kwargs):
        return self._fs.touch(self._format_path(path), **kwargs)


class UPath(pathlib.Path):

    __slots__ = (
        "_url",
        "_kwargs",
        "_accessor",  # overwritten because of default in Python 3.10
    )
    _flavour = pathlib._posix_flavour
    _default_accessor = _FSSpecAccessor

    def __new__(cls, *args, **kwargs) -> Union["UPath", pathlib.Path]:
        args_list = list(args)
        first = args_list.pop(0)
        if isinstance(first, pathlib.PurePath):
            # Create a (modified) copy, if first arg is a Path object
            other = first
            parts = args_list
            drv, root, parts = other._parse_args(parts)
            drv, root, parts = other._flavour.join_parsed_parts(
                other._drv, other._root, other._parts, drv, root, parts
            )

            new_kwargs = getattr(other, "_kwargs", {}).copy()
            new_kwargs.update(kwargs)

            return other.__class__(
                other._format_parsed_parts(drv, root, parts),
                **new_kwargs,
            )

        url = stringify_path(first)
        parsed_url = urllib.parse.urlparse(url)
        for key in ["scheme", "netloc"]:
            val = kwargs.get(key)
            if val:
                parsed_url = parsed_url._replace(**{key: val})

        fsspec_impls = list(registry) + list(known_implementations.keys())
        if parsed_url.scheme and parsed_url.scheme in fsspec_impls:
            import upath.registry

            cls = upath.registry._registry[parsed_url.scheme]
            args_list.insert(0, parsed_url.path)
            return cls._from_parts(tuple(args_list), url=parsed_url, **kwargs)

        # treat as local filesystem, return PosixPath or WindowsPath
        return pathlib.Path(*args, **kwargs)

    def __getattr__(self, item):
        if item == "_accessor":
            # cache the _accessor attribute on first access
            kwargs = self._kwargs.copy()
            self._accessor = _accessor = self._default_accessor(
                self._url, **kwargs
            )
            return _accessor
        else:
            raise AttributeError(item)

    def _make_child(self, args):
        drv, root, parts = self._parse_args(args)
        drv, root, parts = self._flavour.join_parsed_parts(
            self._drv, self._root, self._parts, drv, root, parts
        )
        return self._from_parsed_parts(
            drv, root, parts, url=self._url, **self._kwargs
        )

    def _make_child_relpath(self, part):
        # This is an optimization used for dir walking.  `part` must be
        # a single part relative to this path.
        parts = self._parts + [part]
        return self._from_parsed_parts(
            self._drv, self._root, parts, url=self._url, **self._kwargs
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
        return self._from_parsed_parts(
            drv, root, parts[:-1], url=self._url, **self._kwargs
        )

    def stat(self):
        return self._accessor.stat(self)

    def iterdir(self):
        """Iterate over the files in this directory.  Does not yield any
        result for the special paths '.' and '..'.
        """
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

    def relative_to(self, *other):
        for other_item in other:
            if not isinstance(other_item, self.__class__) and not isinstance(
                other_item, str
            ):
                raise ValueError(
                    f"{repr(self)} and {repr(other_item)} are "
                    "not of compatible classes."
                )
            if not isinstance(other_item, str) and (
                other_item._url.scheme != self._url.scheme
                or other_item._url.netloc != self._url.netloc
                or other_item._kwargs != self._kwargs
            ):
                raise ValueError(
                    f"{self} and {other_item} do not share the same "
                    "base URL and storage options."
                )
        output = super().relative_to(*other)
        output._url = self._url
        output._kwargs = self._kwargs
        return output

    def glob(self, pattern):
        path_pattern = self.joinpath(pattern)
        for name in self._accessor.glob(self, path_pattern):
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
        try:
            info = self._accessor.info(self)
            if info["type"] == "directory":
                return True
        except FileNotFoundError:
            return False
        return False

    def is_file(self):
        try:
            info = self._accessor.info(self)
            if info["type"] == "file":
                return True
        except FileNotFoundError:
            return False
        return False

    def is_mount(self):
        return False

    def is_symlink(self):
        try:
            info = self._accessor.info(self)
            if "islink" in info:
                return info["islink"]
        except FileNotFoundError:
            return False
        return False

    def is_socket(self):
        return False

    def is_fifo(self):
        return False

    def is_block_device(self):
        return False

    def is_char_device(self):
        return False

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

    def chmod(self, mod):
        raise NotImplementedError

    def rename(self, target):
        # can be implemented, but may be tricky
        raise NotImplementedError

    def cwd(self):
        raise NotImplementedError

    def home(self):
        raise NotImplementedError

    def expanduser(self):
        raise NotImplementedError

    def group(self):
        raise NotImplementedError

    def lchmod(self, mode):
        raise NotImplementedError

    def lstat(self):
        raise NotImplementedError

    def owner(self):
        raise NotImplementedError

    def readlink(self):
        raise NotImplementedError

    def touch(self, trunicate=True, **kwargs):
        self._accessor.touch(self, trunicate=trunicate, **kwargs)

    @classmethod
    def _from_parts(cls, args, url=None, **kwargs):
        obj = object.__new__(cls)
        drv, root, parts = obj._parse_args(args)
        obj._drv = drv
        if sys.version_info < (3, 9):
            obj._closed = False
        obj._url = url
        obj._kwargs = kwargs.copy()

        if not root:
            if not parts:
                root = "/"
                parts = ["/"]
            elif parts[0] == "/":
                root = parts[1:]
        obj._root = root
        obj._parts = parts

        return obj

    @classmethod
    def _from_parsed_parts(cls, drv, root, parts, url=None, **kwargs):
        obj = object.__new__(cls)
        obj._drv = drv
        obj._parts = parts
        if sys.version_info < (3, 9):
            obj._closed = False
        obj._url = url
        obj._kwargs = kwargs.copy()

        if not root:
            if not parts:
                root = "/"
            elif parts[0] == "/":
                root = parts.pop(0)
        if len(obj._parts) == 0 or obj._parts[0] != root:
            obj._parts.insert(0, root)

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

        # Create a new object
        out = self.__class__(
            self._format_parsed_parts(drv, root, parts),
            **kwargs,
        )
        return out

    def __setstate__(self, state):
        self._kwargs = state["_kwargs"].copy()

    def __reduce__(self):
        return (
            self.__class__,
            (self._format_parsed_parts(self._drv, self._root, self._parts),),
            {"_kwargs": self._kwargs.copy()},
        )
