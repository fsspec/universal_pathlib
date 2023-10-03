from __future__ import annotations

import os
import posixpath
import re
import sys
import warnings
from copy import copy
from pathlib import Path
from pathlib import PurePath
from typing import TYPE_CHECKING
from typing import Any
from typing import TypeAlias
from typing import cast
from urllib.parse import urlsplit

if sys.version_info >= (3, 11):
    from typing import Self
else:
    Self = Any

from fsspec import AbstractFileSystem
from fsspec import filesystem
from fsspec import get_filesystem_class
from fsspec.core import strip_protocol as fsspec_strip_protocol

from upath.registry import get_upath_class

PathOrStr: TypeAlias = "str | PurePath | os.PathLike"


class _FSSpecAccessor:
    """this is a compatibility shim and will be removed"""


class fsspecpathmod:
    sep: str = "/"
    altsep: str | None = None

    @staticmethod
    def join(__path: PathOrStr, *paths: PathOrStr) -> str:
        return posixpath.join(*map(strip_upath_protocol, [__path, *paths]))

    @staticmethod
    def splitroot(__path: PathOrStr) -> tuple[str, str, str]:
        path = strip_upath_protocol(__path)
        return posixpath.splitroot(path)  # type: ignore

    @staticmethod
    def splitdrive(__path: PathOrStr) -> tuple[str, str]:
        path = strip_upath_protocol(__path)
        return posixpath.splitdrive(path)

    @staticmethod
    def normcase(__path: PathOrStr) -> str:
        return posixpath.normcase(__path)


_PROTOCOL_RE = re.compile(
    r"^(?P<protocol>[A-Za-z][A-Za-z0-9+]+):(?P<slashes>//?)(?P<path>.*)"
)


def split_upath_protocol(pth: str) -> str:
    if m := _PROTOCOL_RE.match(pth):
        return m.group("protocol")
    return ""


def strip_upath_protocol(pth: PathOrStr) -> str:
    if isinstance(pth, PurePath):
        pth = str(pth)
    elif not isinstance(pth, str):
        pth = os.fspath(pth)
    if m := _PROTOCOL_RE.match(pth):
        protocol = m.group("protocol")
        path = m.group("path")
        if len(m.group("slashes")) == 1:
            pth = f"{protocol}:///{path}"
        return fsspec_strip_protocol(pth)
    else:
        return pth


def get_upath_protocol(
    pth: str | PurePath,
    *,
    protocol: str | None = None,
    storage_options: dict[str, Any] | None = None,
) -> str:
    """return the filesystem spec protocol"""
    if isinstance(pth, str):
        pth_protocol = split_upath_protocol(pth)
    elif isinstance(pth, UPath):
        pth_protocol = pth.protocol
    elif isinstance(pth, PurePath):
        pth_protocol = ""
    else:
        raise TypeError("expected a str or PurePath instance")
    # if storage_options and not protocol:
    #     protocol = "file"
    if protocol and pth_protocol and protocol != pth_protocol:
        raise ValueError(
            f"requested protocol {protocol!r} incompatible with {pth_protocol!r}"
        )
    return protocol or pth_protocol or ""


def _get_pathmod(arg: PurePath) -> fsspecpathmod:
    try:
        return arg.pathmod  # type: ignore
    except AttributeError:
        return arg._flavour  # type: ignore


class UPath(Path):
    __slots__ = (
        "_protocol",
        "_storage_options",
        "_fs_cached",
    )
    if TYPE_CHECKING:
        _protocol: str
        _storage_options: dict[str, Any]
        _fs_cached: AbstractFileSystem

    pathmod = _flavour = fsspecpathmod

    def __new__(
        cls, *args, protocol: str | None = None, **storage_options: Any
    ) -> UPath:
        # fill empty arguments
        if not args:
            args = (".",)

        # create a copy if UPath class
        part0, *parts = args
        if not parts and not storage_options and isinstance(part0, cls):
            return copy(part0)

        # deprecate 'scheme'
        if "scheme" in storage_options:
            warnings.warn(
                "use 'protocol' kwarg instead of 'scheme'",
                DeprecationWarning,
                stacklevel=2,
            )
            protocol = storage_options.pop("scheme")

        # determine which UPath subclass to dispatch to
        pth_protocol = get_upath_protocol(
            part0, protocol=protocol, storage_options=storage_options
        )
        upath_cls = get_upath_class(protocol=pth_protocol)
        if upath_cls is None:
            raise ValueError(f"Unsupported filesystem: {pth_protocol!r}")

        # create a new instance
        obj: UPath = cast("UPath", object.__new__(upath_cls))
        obj._protocol = pth_protocol

        if cls is not UPath and not issubclass(upath_cls, cls):
            msg = (
                f"{cls.__name__!s}(...) detected protocol {pth_protocol!r} and"
                f" returns a {upath_cls.__name__} instance that isn't a direct"
                f" subclass of {cls.__name__}. This will raise an exception in"
                " future universal_pathlib versions. To prevent the issue, use"
                " UPath(...) to create instances of unrelated protocols or the"
                f" {cls.__name__} class can be registered with the protocol to"
                f" override the default implementation for {pth_protocol!r}."
            )
            warnings.warn(msg, DeprecationWarning, stacklevel=2)
            upath_cls.__init__(
                obj, *args, protocol=pth_protocol, **storage_options
            )  # type: ignore

        return obj

    def __init__(
        self, *args, protocol: str | None = None, **storage_options: Any
    ) -> None:
        # retrieve storage_options
        if args:
            args0 = args[0]
            if isinstance(args0, UPath):
                self._storage_options = {**args0.storage_options, **storage_options}
            else:
                fs_cls: type[AbstractFileSystem] = get_filesystem_class(
                    protocol or self._protocol
                )
                pth_storage_options = fs_cls._get_kwargs_from_urls(str(args0))
                self._storage_options = {**pth_storage_options, **storage_options}
        else:
            self._storage_options = storage_options.copy()

        # check that UPath subclasses in args are compatible
        # --> ensures items in _raw_paths are compatible
        for arg in args:
            if not isinstance(arg, UPath):
                continue
            # protocols: only identical (or empty "") protocols can combine
            if arg.protocol and arg.protocol != self._protocol:
                raise TypeError("can't combine different UPath protocols as parts")
            # storage_options: args may not define other storage_options
            if any(
                self._storage_options.get(key) != value
                for key, value in arg.storage_options.items()
            ):
                # raise ValueError(
                #     "can't combine different UPath storage_options as parts"
                # ) todo: revisit and define behaviour
                pass

        # fill ._raw_paths
        super().__init__(*args)

    # === upath.UPath only ============================================

    @property
    def protocol(self) -> str:
        return self._protocol

    @property
    def storage_options(self) -> dict[str, Any]:
        return self._storage_options

    @property
    def fs(self) -> AbstractFileSystem:
        try:
            return self._fs_cached
        except AttributeError:
            fs = self._fs_cached = filesystem(
                protocol=self.protocol, **self.storage_options
            )
            return fs

    @property
    def path(self) -> str:
        return super().__str__()

    @property
    def _kwargs(self):
        warnings.warn(
            "use UPath.storage_options instead of UPath._kwargs",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.storage_options

    @property
    def _url(self):
        return urlsplit(str(self))  # todo: deprecate

    # === pathlib.PurePath ============================================

    def __reduce__(self):
        state = {
            "_protocol": self._protocol,
            "_storage_options": self._storage_options,
        }
        return (self.__class__, tuple(self._raw_paths), (None, state))

    def with_segments(self, *pathsegments):
        return type(self)(
            *pathsegments,
            protocol=self._protocol,
            **self._storage_options,
        )

    def __str__(self):
        if self._protocol:
            return f"{self._protocol}://{self.path}"
        else:
            return self.path

    def __fspath__(self):
        msg = (
            "in a future version of UPath this will be set to None"
            " unless the filesystem is local (or caches locally)"
        )
        warnings.warn(msg, PendingDeprecationWarning, stacklevel=2)
        return str(self)

    def __bytes__(self):
        msg = (
            "in a future version of UPath this will be set to None"
            " unless the filesystem is local (or caches locally)"
        )
        warnings.warn(msg, PendingDeprecationWarning, stacklevel=2)
        return os.fsencode(self)

    def as_uri(self):
        return str(self)

    def is_reserved(self):
        return False

    def relative_to(self, other, /, *_deprecated, walk_up=False):
        if isinstance(other, UPath) and self.storage_options != other.storage_options:
            raise ValueError(
                "paths have different storage_options:"
                f" {self.storage_options!r} != {other.storage_options!r}"
            )
        return super().relative_to(other, *_deprecated, walk_up=walk_up)

    def is_relative_to(self, other, /, *_deprecated):
        if isinstance(other, UPath) and self.storage_options != other.storage_options:
            return False
        return super().is_relative_to(other, *_deprecated)

    # === pathlib.Path ================================================

    def stat(self, *, follow_symlinks=True):
        return self.fs.stat(self.path)

    def lstat(self):
        # return self.stat(follow_symlinks=False)
        raise NotImplementedError

    def exists(self, *, follow_symlinks=True):
        return self.fs.exists(self.path)

    def is_dir(self):
        return self.fs.isdir(self.path)

    def is_file(self):
        return self.fs.isfile(self.path)

    def is_mount(self):
        return False

    def is_symlink(self):
        try:
            info = self.fs.info(self.path)
            if "islink" in info:
                return bool(info["islink"])
        except FileNotFoundError:
            return False
        return False

    def is_junction(self):
        return False

    def is_block_device(self):
        return False

    def is_char_device(self):
        return False

    def is_fifo(self):
        return False

    def is_socket(self):
        return False

    def samefile(self, other_path):
        raise NotImplementedError

    def open(self, mode="r", buffering=-1, encoding=None, errors=None, newline=None):
        return self.fs.open(self.path, mode)  # fixme

    def iterdir(self):
        for name in self.fs.listdir(self.path):
            # fsspec returns dictionaries
            if isinstance(name, dict):
                name = name.get("name")
            if name in {".", ".."}:
                # Yielding a path object for these makes little sense
                continue
            # only want the path name with iterdir
            _, _, name = name.rpartition(self._flavour.sep)
            yield self._make_child_relpath(name)

    def _scandir(self):
        # return os.scandir(self)
        raise NotImplementedError

    def _make_child_relpath(self, name):
        path = super()._make_child_relpath(name)
        del path._str  # fix _str = str(self) assignment
        return path

    def glob(self, pattern: str, *, case_sensitive=None):
        path_pattern = self.joinpath(pattern).path
        sep = self._flavour.sep
        for name in self.fs.glob(path_pattern):
            name = name.removeprefix(self.path).removeprefix(sep)
            yield self.joinpath(name)

    def rglob(self, pattern: str, *, case_sensitive=None):
        r_path_pattern = self.joinpath("**", pattern).path
        sep = self._flavour.sep
        for name in self.fs.glob(r_path_pattern):
            name = name.removeprefix(self.path).removeprefix(sep)
            yield self.joinpath(name)

    @classmethod
    def cwd(cls):
        if cls is UPath:
            return get_upath_class("").cwd()
        else:
            raise NotImplementedError

    @classmethod
    def home(cls):
        if cls is UPath:
            return get_upath_class("").home()
        else:
            raise NotImplementedError

    def absolute(self) -> Self:
        return self

    def resolve(self, strict: bool = False) -> Self:
        _parts = self.parts

        # Do not attempt to normalize path if no parts are dots
        if ".." not in _parts and "." not in _parts:
            return self

        resolved: list[str] = []
        resolvable_parts = _parts[1:]
        for part in resolvable_parts:
            if part == "..":
                if resolved:
                    resolved.pop()
            elif part != ".":
                resolved.append(part)

        return self.with_segments(*_parts[:1], *resolved)

    def owner(self):
        raise NotImplementedError

    def group(self):
        raise NotImplementedError

    def readlink(self):
        raise NotImplementedError

    def touch(self, mode=0o666, exist_ok=True):
        self.fs.touch(self.path, truncate=not exist_ok)

    def mkdir(self, mode=0o777, parents=False, exist_ok=False):
        if parents:
            if not exist_ok and self.exists():
                raise FileExistsError(str(self))
            self.fs.makedirs(self.path, exist_ok=exist_ok)
        else:
            try:
                self.fs.mkdir(
                    self.path,
                    create_parents=False,
                    mode=mode,
                )
            except FileExistsError:
                if not exist_ok or not self.is_dir():
                    raise FileExistsError(str(self))

    def chmod(self, mode, *, follow_symlinks=True):
        raise NotImplementedError

    def unlink(self, missing_ok=False):
        if not self.exists():
            if not missing_ok:
                raise FileNotFoundError(str(self))
            return
        self.fs.rm(self.path, recursive=False)

    def rmdir(self, recursive: bool = True):  # fixme: non-standard
        if not self.is_dir():
            raise NotADirectoryError(str(self))
        if not recursive and next(self.iterdir()):
            raise OSError(f"Not recursive and directory not empty: {self}")
        self.fs.rm(self.path, recursive=recursive)

    def rename(self, target, *, recursive=False, maxdepth=None, **kwargs):
        if not isinstance(target, UPath):
            target = self.parent.joinpath(target).resolve()
        self.fs.mv(
            self.path,
            target.path,
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

    def expanduser(self):
        raise NotImplementedError
