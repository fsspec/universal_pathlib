from __future__ import annotations

import re
import sys
from os import PathLike
from pathlib import Path
from pathlib import PurePath
from pathlib import _PosixFlavour  # type: ignore
from typing import TYPE_CHECKING
from typing import Sequence
from typing import TypeVar
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

from fsspec.registry import get_filesystem_class
from fsspec.utils import stringify_path

from upath.registry import get_upath_class

if TYPE_CHECKING:
    from typing import Any
    from typing import Generator
    from urllib.parse import SplitResult

    from fsspec.spec import AbstractFileSystem

__all__ = [
    "UPath",
]


class _FSSpecAccessor:
    __slots__ = ("_fs",)

    def __init__(self, parsed_url: SplitResult | None, **kwargs: Any) -> None:
        if parsed_url:
            cls = get_filesystem_class(parsed_url.scheme)
            url_kwargs = cls._get_kwargs_from_urls(urlunsplit(parsed_url))
        else:
            cls = get_filesystem_class(None)
            url_kwargs = {}
        url_kwargs.update(kwargs)
        self._fs = cls(**url_kwargs)

    def _format_path(self, path: UPath) -> str:
        return path.path

    def open(self, path, mode="r", *args, **kwargs):
        return self._fs.open(self._format_path(path), mode, *args, **kwargs)

    def stat(self, path, **kwargs):
        return self._fs.stat(self._format_path(path), **kwargs)

    def listdir(self, path, **kwargs):
        p_fmt = self._format_path(path)
        contents = self._fs.listdir(p_fmt, **kwargs)
        if len(contents) == 0 and not self._fs.isdir(p_fmt):
            raise NotADirectoryError(str(self))
        elif (
            len(contents) == 1
            and contents[0]["name"] == p_fmt
            and contents[0]["type"] == "file"
        ):
            raise NotADirectoryError(str(self))
        return contents

    def glob(self, _path, path_pattern, **kwargs):
        return self._fs.glob(self._format_path(path_pattern), **kwargs)

    def exists(self, path, **kwargs):
        return self._fs.exists(self._format_path(path), **kwargs)

    def info(self, path, **kwargs):
        return self._fs.info(self._format_path(path), **kwargs)

    def rm(self, path, recursive, **kwargs):
        return self._fs.rm(self._format_path(path), recursive=recursive, **kwargs)

    def mkdir(self, path, create_parents=True, **kwargs):
        return self._fs.mkdir(
            self._format_path(path), create_parents=create_parents, **kwargs
        )

    def makedirs(self, path, exist_ok=False, **kwargs):
        return self._fs.makedirs(self._format_path(path), exist_ok=exist_ok, **kwargs)

    def touch(self, path, **kwargs):
        return self._fs.touch(self._format_path(path), **kwargs)

    def mv(self, path, target, recursive=False, maxdepth=None, **kwargs):
        if hasattr(target, "_accessor"):
            target = target._accessor._format_path(target)
        return self._fs.mv(
            self._format_path(path),
            target,
            recursive=recursive,
            maxdepth=maxdepth,
            **kwargs,
        )


class _UriFlavour(_PosixFlavour):
    def parse_parts(self, parts):
        parsed = []
        sep = self.sep
        drv = root = ""
        it = reversed(parts)
        for part in it:
            if part:
                drv, root, rel = self.splitroot(part)
                if not root or root and rel:
                    for x in reversed(rel.split(sep)):
                        parsed.append(sys.intern(x))

        if drv or root:
            parsed.append(drv + root)
        parsed.reverse()
        return drv, root, parsed

    def splitroot(self, part, sep="/"):
        # Treat the first slash in the path as the root if it exists
        if part and part[0] == sep:
            return "", sep, part[1:]
        return "", "", part


PT = TypeVar("PT", bound="UPath")


class UPath(Path):
    __slots__ = (
        "_url",
        "_kwargs",
        "_accessor",  # overwritten because of default in Python 3.10
    )
    _flavour = _UriFlavour()
    _default_accessor = _FSSpecAccessor

    # typing
    _drv: str
    _root: str
    _str: str
    _url: SplitResult | None
    _parts: list[str]
    _closed: bool
    _accessor: _FSSpecAccessor

    def __new__(cls: type[PT], *args: str | PathLike, **kwargs: Any) -> PT:
        args_list = list(args)
        other = args_list.pop(0)

        if isinstance(other, PurePath):
            # Create a (modified) copy, if first arg is a Path object
            _cls: type[Any] = type(other)
            drv, root, parts = _cls._parse_args(args_list)
            drv, root, parts = _cls._flavour.join_parsed_parts(
                other._drv, other._root, other._parts, drv, root, parts  # type: ignore # noqa: E501
            )

            _kwargs = getattr(other, "_kwargs", {})
            _url = getattr(other, "_url", None)
            other_kwargs = _kwargs.copy()
            if _url:
                other_kwargs["url"] = _url
            new_kwargs = _kwargs.copy()
            new_kwargs.update(kwargs)

            return _cls(  # type: ignore
                _cls._format_parsed_parts(drv, root, parts, **other_kwargs),
                **new_kwargs,
            )

        url = stringify_path(other)
        parsed_url = urlsplit(url)
        if not parsed_url.path:
            parsed_url = parsed_url._replace(path="/")  # ensure path has root

        for key in ["scheme", "netloc"]:
            val = kwargs.get(key)
            if val:
                parsed_url = parsed_url._replace(**{key: val})

        upath_cls = get_upath_class(protocol=parsed_url.scheme)
        if upath_cls is None:
            # treat as local filesystem, return PosixPath or WindowsPath
            return Path(*args, **kwargs)  # type: ignore

        args_list.insert(0, parsed_url.path)
        # return upath instance
        return upath_cls._from_parts(  # type: ignore
            args_list, url=parsed_url, **kwargs
        )

    def __getattr__(self, item: str) -> Any:
        if item == "_accessor":
            # cache the _accessor attribute on first access
            kwargs = self._kwargs.copy()
            self._accessor = _accessor = self._default_accessor(self._url, **kwargs)
            return _accessor
        else:
            raise AttributeError(item)

    def _make_child(self: PT, args: list[str]) -> PT:
        drv, root, parts = self._parse_args(args)
        drv, root, parts = self._flavour.join_parsed_parts(
            self._drv, self._root, self._parts, drv, root, parts
        )
        return self._from_parsed_parts(drv, root, parts, url=self._url, **self._kwargs)

    def _make_child_relpath(self: PT, part: str) -> PT:
        # This is an optimization used for dir walking.  `part` must be
        # a single part relative to this path.
        parts = self._parts + [part]
        return self._from_parsed_parts(
            self._drv, self._root, parts, url=self._url, **self._kwargs
        )

    @classmethod
    def _format_parsed_parts(
        cls: type[PT],
        drv: str,
        root: str,
        parts: list[str],
        url: SplitResult | None = None,
        **kwargs: Any,
    ) -> str:
        if parts:
            join_parts = parts[1:] if parts[0] == "/" else parts
        else:
            join_parts = []
        if drv or root:
            path: str = drv + root + cls._flavour.join(join_parts)
        else:
            path = cls._flavour.join(join_parts)
        if not url:
            scheme: str = kwargs.get("scheme", "file")
            netloc: str = kwargs.get("netloc", "")
        else:
            scheme, netloc = url.scheme, url.netloc
        scheme = scheme + ":"
        netloc = "//" + netloc if netloc else ""
        formatted = scheme + netloc + path
        return formatted

    @property
    def path(self) -> str:
        if self._parts:
            join_parts = self._parts[1:] if self._parts[0] == "/" else self._parts
            path: str = self._flavour.join(join_parts)
            return self._root + path
        else:
            return "/"

    def open(self, *args, **kwargs):
        return self._accessor.open(self, *args, **kwargs)

    @property
    def parent(self: PT) -> PT:
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

    def samefile(self, other_path) -> bool:
        raise NotImplementedError

    def iterdir(self: PT) -> Generator[PT, None, None]:
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

    def relative_to(self: PT, *other: str | PathLike) -> PT:
        for other_item in other:
            if not isinstance(other_item, self.__class__) and not isinstance(
                other_item, str
            ):
                raise ValueError(
                    f"{repr(self)} and {repr(other_item)} are "
                    "not of compatible classes."
                )
            if not isinstance(other_item, str) and (
                self._url is None
                or other_item._url is None
                or other_item._url.scheme != self._url.scheme
                or other_item._url.netloc != self._url.netloc
                or other_item._kwargs != self._kwargs
            ):
                raise ValueError(
                    f"{self} and {other_item} do not share the same "
                    "base URL and storage options."
                )
        output: PT = super().relative_to(*other)  # type: ignore
        output._url = self._url
        output._kwargs = self._kwargs
        return output

    def _scandir(self):
        # provided in Python3.11 but not required in fsspec glob implementation
        raise NotImplementedError

    def glob(self: PT, pattern: str) -> Generator[PT, None, None]:
        path_pattern = self.joinpath(pattern)
        for name in self._accessor.glob(self, path_pattern):
            name = self._sub_path(name)
            name = name.split(self._flavour.sep)
            yield self._make_child(name)

    def rglob(self: PT, pattern: str) -> Generator[PT, None, None]:
        path_pattern = self.joinpath(pattern)
        r_path_pattern = self.joinpath("**", pattern)
        for p in (path_pattern, r_path_pattern):
            for name in self._accessor.glob(self, p):
                name = self._sub_path(name)
                name = name.split(self._flavour.sep)
                yield self._make_child(name)

    def _sub_path(self, name):
        # only want the path name with iterdir
        sp = self.path
        return re.sub(f"^({sp}|{sp[1:]})/", "", name)

    def absolute(self: PT) -> PT:
        # fsspec paths are always absolute
        return self

    def resolve(self: PT, strict: bool = False) -> PT:
        """Return a new path with '.' and '..' parts normalized."""
        _parts = self._parts

        # Do not attempt to normalize path if no parts are dots
        if ".." not in _parts and "." not in _parts:
            return self

        sep = self._flavour.sep

        resolved: list[str] = []
        resolvable_parts = _parts[1:]
        idx_max = len(resolvable_parts) - 1
        for i, part in enumerate(resolvable_parts):
            if part == "..":
                if resolved:
                    resolved.pop()
            elif part != ".":
                if i < idx_max:
                    part += sep
                resolved.append(part)

        path = "".join(resolved)
        url = self._url
        if url is not None:
            url = url._replace(path=path)
        parts = _parts[:1] + path.split(sep)

        return self._from_parsed_parts(
            self._drv,
            self._root,
            parts,
            url=url,
            **self._kwargs,
        )

    def exists(self) -> bool:
        """Check whether this path exists or not."""
        accessor = self._accessor
        try:
            return bool(accessor.exists(self))
        except AttributeError:
            try:
                self._accessor.stat(self)
            except FileNotFoundError:
                return False
            return True

    def is_dir(self) -> bool:
        try:
            info = self._accessor.info(self)
            if info["type"] == "directory":
                return True
        except FileNotFoundError:
            return False
        return False

    def is_file(self) -> bool:
        try:
            info = self._accessor.info(self)
            if info["type"] == "file":
                return True
        except FileNotFoundError:
            return False
        return False

    def is_mount(self) -> bool:
        return False

    def is_symlink(self) -> bool:
        try:
            info = self._accessor.info(self)
            if "islink" in info:
                return bool(info["islink"])
        except FileNotFoundError:
            return False
        return False

    def is_socket(self) -> bool:
        return False

    def is_fifo(self) -> bool:
        return False

    def is_block_device(self) -> bool:
        return False

    def is_char_device(self) -> bool:
        return False

    def is_absolute(self) -> bool:
        return True

    def unlink(self, missing_ok: bool = False) -> None:
        if not self.exists():
            if not missing_ok:
                raise FileNotFoundError(str(self))
            return
        self._accessor.rm(self, recursive=False)

    def rmdir(self, recursive: bool = True) -> None:
        if not self.is_dir():
            raise NotADirectoryError(str(self))
        if not recursive and next(self.iterdir()):  # type: ignore
            raise OSError(f"Not recursive and directory not empty: {self}")
        self._accessor.rm(self, recursive=recursive)

    def chmod(self, mode, *, follow_symlinks: bool = True) -> None:
        raise NotImplementedError

    def rename(self, target, recursive=False, maxdepth=None, **kwargs):
        """Move file, see `fsspec.AbstractFileSystem.mv`."""
        if not isinstance(target, UPath):
            target = self.parent.joinpath(target).resolve()
        self._accessor.mv(
            self,
            target,
            recursive=recursive,
            maxdepth=maxdepth,
            **kwargs,
        )
        return target

    def replace(self, target):
        raise NotImplementedError

    def symlink_to(self, target, target_is_directory=False):
        raise NotImplementedError

    def hardlink_to(self, target):
        raise NotImplementedError

    def link_to(self, target):
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

    def touch(self, *args: int, truncate: bool = True, **kwargs) -> None:
        # Keep the calling signature compatible with Path
        # (without changing current fsspec behavior for defaults)
        if len(args) > 2:
            raise TypeError("too many arguments")
        else:
            for key, val in zip(["mode", "exists_ok"], args):
                if key in kwargs:
                    raise TypeError(f"provided {key!r} as arg and kwarg")
                kwargs[key] = val
        self._accessor.touch(self, truncate=truncate, **kwargs)

    def mkdir(
        self, mode: int = 0o777, parents: bool = False, exist_ok: bool = False
    ) -> None:
        """
        Create a new directory at this given path.
        """
        if parents:
            if not exist_ok and self.exists():
                raise FileExistsError(str(self))
            self._accessor.makedirs(self, exist_ok=exist_ok)
        else:
            try:
                self._accessor.mkdir(
                    self,
                    create_parents=False,
                    mode=mode,
                )
            except FileExistsError:
                if not exist_ok or not self.is_dir():
                    raise FileExistsError(str(self))

    @classmethod
    def _from_parts(
        cls: type[PT],
        args: list[str | PathLike],
        url: SplitResult | None = None,
        **kwargs: Any,
    ) -> PT:
        obj = object.__new__(cls)
        drv, root, parts = obj._parse_args(args)
        obj._drv = drv
        if sys.version_info < (3, 9):
            obj._closed = False
        obj._kwargs = kwargs.copy()

        if not root:
            if not parts:
                root = "/"
                parts = ["/"]
            elif parts[0] == "/":
                root = parts[1:]
        obj._root = root
        obj._parts = parts

        # Update to (full) URL
        if url:
            url = url._replace(path=root + cls._flavour.join(parts[1:]))
        obj._url = url

        return obj

    @classmethod
    def _from_parsed_parts(
        cls: type[PT],
        drv: str,
        root: str,
        parts: list[str],
        url: SplitResult | None = None,
        **kwargs: Any,
    ) -> PT:
        obj = object.__new__(cls)
        obj._drv = drv
        obj._parts = parts
        if sys.version_info < (3, 9):
            obj._closed = False
        obj._kwargs = kwargs.copy()

        if not root:
            if not parts:
                root = "/"
            elif parts[0] == "/":
                root = parts.pop(0)
        if len(obj._parts) == 0 or obj._parts[0] != root:
            obj._parts.insert(0, root)
        obj._root = root

        if url:
            url = url._replace(path=root + cls._flavour.join(parts[1:]))
        obj._url = url
        return obj

    def __str__(self) -> str:
        """Return the string representation of the path, suitable for
        passing to system calls."""
        try:
            return self._str
        except AttributeError:
            self._str = self._format_parsed_parts(
                self._drv,
                self._root,
                self._parts,
                url=self._url,
                **self._kwargs,
            )
            return self._str

    @property
    def fs(self) -> AbstractFileSystem:
        return self._accessor._fs

    def __truediv__(self: PT, key: str | PathLike) -> PT:
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
            self._format_parsed_parts(drv, root, parts, url=self._url),
            **kwargs,
        )
        return out

    def __setstate__(self, state: dict) -> None:
        self._kwargs = state["_kwargs"].copy()

    def __reduce__(self):
        cls = type(self)
        return (
            cls,
            (
                cls._format_parsed_parts(
                    self._drv, self._root, self._parts, url=self._url
                ),
            ),
            {"_kwargs": self._kwargs.copy()},
        )

    def with_suffix(self: PT, suffix: str) -> PT:
        """Return a new path with the file suffix changed.  If the path
        has no suffix, add given suffix.  If the given suffix is an empty
        string, remove the suffix from the path.
        """
        f = self._flavour
        if f.sep in suffix or f.altsep and f.altsep in suffix:
            raise ValueError(f"Invalid suffix {suffix!r}")
        if suffix and not suffix.startswith(".") or suffix == ".":
            raise ValueError("Invalid suffix %r" % (suffix))
        name = self.name
        if not name:
            raise ValueError(f"{self!r} has an empty name")
        old_suffix = self.suffix
        if not old_suffix:
            name = name + suffix
        else:
            name = name[: -len(old_suffix)] + suffix
        return self._from_parsed_parts(
            self._drv,
            self._root,
            self._parts[:-1] + [name],
            url=self._url,
            **self._kwargs,
        )

    def with_name(self: PT, name: str) -> PT:
        """Return a new path with the file name changed."""
        if not self.name:
            raise ValueError(f"{self!r} has an empty name")
        drv, root, parts = self._flavour.parse_parts((name,))
        if (
            not name
            or name[-1] in [self._flavour.sep, self._flavour.altsep]
            or drv
            or root
            or len(parts) != 1
        ):
            raise ValueError("Invalid name %r" % (name))
        return self._from_parsed_parts(
            self._drv,
            self._root,
            self._parts[:-1] + [name],
            url=self._url,
            **self._kwargs,
        )

    @property
    def parents(self) -> _UPathParents:
        """A sequence of this upath's logical parents."""
        return _UPathParents(self)


class _UPathParents(Sequence[UPath]):
    """This object provides sequence-like access to the logical ancestors
    of a path.  Don't try to construct it yourself."""

    __slots__ = (
        "_pathcls",
        "_drv",
        "_root",
        "_parts",
        "_url",
        "_kwargs",
    )

    def __init__(self, path):
        # We don't store the instance to avoid reference cycles
        self._pathcls = type(path)
        self._drv = path._drv
        self._root = path._root
        self._parts = path._parts
        self._url = path._url
        self._kwargs = path._kwargs

    def __len__(self):
        if self._drv or self._root:
            return len(self._parts) - 1
        else:
            return len(self._parts)

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return tuple(self[i] for i in range(*idx.indices(len(self))))

        if idx >= len(self) or idx < -len(self):
            raise IndexError(idx)
        if idx < 0:
            idx += len(self)
        return self._pathcls._from_parsed_parts(
            self._drv,
            self._root,
            self._parts[: -idx - 1],
            url=self._url,
            **self._kwargs,
        )

    def __repr__(self):
        return f"<{self._pathcls.__name__}.parents>"
