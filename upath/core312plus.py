from __future__ import annotations

import os
import posixpath
import sys
import warnings
from copy import copy
from pathlib import Path
from pathlib import PurePath
from types import MappingProxyType
from typing import TYPE_CHECKING
from typing import Any
from typing import Mapping
from typing import TypeAlias
from typing import cast
from urllib.parse import SplitResult
from urllib.parse import urlsplit

if sys.version_info >= (3, 11):
    from typing import Self
else:
    Self = Any

from fsspec import AbstractFileSystem
from fsspec import get_filesystem_class

from upath._protocol import get_upath_protocol
from upath._protocol import strip_upath_protocol
from upath.registry import get_upath_class

PathOrStr: TypeAlias = "str | PurePath | os.PathLike"


class _FSSpecAccessor:
    """this is a compatibility shim and will be removed"""

    def __init__(self, parsed_url: SplitResult | None, **kwargs: Any) -> None:
        pass


class FSSpecFlavour:
    """fsspec flavour for universal_pathlib

    **INTERNAL AND VERY MUCH EXPERIMENTAL**

    Implements the fsspec compatible low-level lexical operations on
    PurePathBase-like objects.

    Note:
        In case you find yourself in need of subclassing FSSpecFlavour,
        please open an issue in the universal_pathlib issue tracker:
        https://github.com/fsspec/universal_pathlib/issues
        Ideally we can find a way to make your use-case work by adding
        more functionality to this class.

    """

    def __init__(
        self,
        *,
        # URI behavior
        join_prepends_protocol: bool = False,
        join_like_urljoin: bool = False,
        supports_empty_parts: bool = False,
        supports_netloc: bool = False,
        supports_query_parameters: bool = False,
        supports_fragments: bool = False,
        posixpath_only: bool = True,
        # configurable separators
        sep: str = "/",
        altsep: str | None = None,
    ):
        self._owner = None
        # separators
        self.sep = sep
        self.altsep = altsep
        # configuration
        self.join_prepends_protocol = join_prepends_protocol
        self.join_like_urljoin = join_like_urljoin
        self.supports_empty_parts = supports_empty_parts
        self.supports_netloc = supports_netloc
        self.supports_query_parameters = supports_query_parameters
        self.supports_fragments = supports_fragments
        self.posixpath_only = posixpath_only

    def __set_name__(self, owner, name):
        # helper to provide a more informative repr
        self._owner = owner.__name__

    def _asdict(self) -> dict[str, Any]:
        """return a dict representation of the flavour's settings"""
        dct = vars(self).copy()
        dct.pop("_owner")
        return dct

    def __repr__(self):
        return f"<{__name__}.{type(self).__name__} of {self._owner}>"

    def join(self, __path: PathOrStr, *paths: PathOrStr) -> str:
        """Join two or more path components, inserting '/' as needed."""
        path = strip_upath_protocol(__path)
        paths = map(strip_upath_protocol, paths)

        if self.join_like_urljoin:
            path = path.removesuffix("/")
            sep = self.sep
            for b in paths:
                if b.startswith(sep):
                    path = b
                elif not path:
                    path += b
                else:
                    path += sep + b
            joined = path
        elif self.posixpath_only:
            joined = posixpath.join(path, *paths)
        else:
            joined = os.path.join(path, *paths)

        if self.join_prepends_protocol and (protocol := get_upath_protocol(__path)):
            joined = f"{protocol}://{joined}"

        return joined

    def splitroot(self, __path: PathOrStr) -> tuple[str, str, str]:
        """Split a path in the drive, the root and the rest."""
        if self.supports_fragments or self.supports_query_parameters:
            url = urlsplit(__path)
            drive = url._replace(path="", query="", fragment="").geturl()
            path = url._replace(scheme="", netloc="").geturl()
            # root = "/" if path.startswith("/") else ""
            root = "/"  # emulate upath.core.UPath < 3.12 behaviour
            return drive, root, path.removeprefix("/")

        path = strip_upath_protocol(__path)
        if self.supports_netloc:
            protocol = get_upath_protocol(__path)
            if protocol:
                drive, root, tail = path.partition("/")
                return drive, root or "/", tail
            else:
                return "", "", path
        elif self.posixpath_only:
            return posixpath.splitroot(path)
        else:
            drv, root, path = os.path.splitroot(path)
            if os.name == "nt" and not drv:
                drv = "C:"
            return drv, root, path

    def splitdrive(self, __path: PathOrStr) -> tuple[str, str]:
        """Split a path into drive and path."""
        if self.supports_fragments or self.supports_query_parameters:
            path = strip_upath_protocol(__path)
            url = urlsplit(path)
            path = url._replace(scheme="", netloc="").geturl()
            drive = url._replace(path="", query="", fragment="").geturl()
            return drive, path

        path = strip_upath_protocol(__path)
        if self.supports_netloc:
            protocol = get_upath_protocol(__path)
            if protocol:
                drive, root, tail = path.partition("/")
                return drive, f"{root}{tail}"
            else:
                return "", path
        elif self.posixpath_only:
            return posixpath.splitdrive(path)
        else:
            drv, path = os.path.splitdrive(path)
            if os.name == "nt" and not drv:
                drv = "C:"
            return drv, path

    def normcase(self, __path: PathOrStr) -> str:
        """Normalize case of pathname. Has no effect under Posix"""
        if self.posixpath_only:
            return posixpath.normcase(__path)
        else:
            return os.path.normcase(__path)


def _make_instance(cls, args, kwargs):
    """helper for pickling UPath instances"""
    return cls(*args, **kwargs)


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

    _flavour = FSSpecFlavour()

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
        if cls is UPath:
            # we called UPath() directly, and want an instance based on the
            # provided or detected protocol (i.e. upath_cls)
            obj: UPath = cast("UPath", object.__new__(upath_cls))
            obj._protocol = pth_protocol

        elif issubclass(cls, upath_cls):
            # we called a sub- or sub-sub-class of UPath, i.e. S3Path() and the
            # corresponding upath_cls based on protocol is equal-to or a
            # parent-of the cls.
            obj = cast("UPath", object.__new__(cls))  # type: ignore[unreachable]
            obj._protocol = pth_protocol

        elif issubclass(cls, UPath):
            # we called a subclass of UPath directly, i.e. S3Path() but the
            # detected protocol would return a non-related UPath subclass, i.e.
            # S3Path("file:///abc"). This behavior is going to raise an error
            # in future versions
            msg_protocol = repr(pth_protocol)
            if not pth_protocol:
                msg_protocol += " (empty string)"
            msg = (
                f"{cls.__name__!s}(...) detected protocol {msg_protocol!s} and"
                f" returns a {upath_cls.__name__} instance that isn't a direct"
                f" subclass of {cls.__name__}. This will raise an exception in"
                " future universal_pathlib versions. To prevent the issue, use"
                " UPath(...) to create instances of unrelated protocols or you"
                f" can instead derive your subclass {cls.__name__!s}(...) from"
                f" {upath_cls.__name__} or alternatively override behavior via"
                f" registering the {cls.__name__} implementation with protocol"
                f" {msg_protocol!s} replacing the default implementation."
            )
            warnings.warn(msg, DeprecationWarning, stacklevel=2)

            obj = cast("UPath", object.__new__(upath_cls))
            obj._protocol = pth_protocol

            upath_cls.__init__(
                obj, *args, protocol=pth_protocol, **storage_options
            )  # type: ignore

        else:
            raise RuntimeError("UPath.__new__ expected cls to be subclass of UPath")

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
    def storage_options(self) -> Mapping[str, Any]:
        return MappingProxyType(self._storage_options)

    def __init_subclass__(cls, **kwargs):
        """provide a clean migration path for custom user subclasses"""

        accessor_cls = getattr(cls, "_default_accessor", None)

        # guess which parts the user subclass is customizing
        has_custom_legacy_accessor = (
            accessor_cls is not None
            and issubclass(accessor_cls, _FSSpecAccessor)
            and accessor_cls is not _FSSpecAccessor
        )
        has_customized_fs_instantiation = (
            accessor_cls.__init__ is not _FSSpecAccessor.__init__
            or hasattr(accessor_cls, "_fs")
        )

        if has_custom_legacy_accessor and has_customized_fs_instantiation:
            warnings.warn(
                "Detected a customized `__init__` method or `_fs` attribute"
                " in the provided `_FSSpecAccessor` subclass. It is recommended to"
                " instead override the `_fs_factory` classmethod to customize"
                " filesystem instantiation.",
                DeprecationWarning,
                stacklevel=2,
            )

            def _fs_factory(
                cls_, urlpath: str, protocol: str, storage_options: Mapping[str, Any]
            ) -> AbstractFileSystem:
                url = urlsplit(urlpath)
                if protocol:
                    url = url._replace(scheme=protocol)
                inst = cls_._default_accessor(url, **storage_options)
                return inst._fs

            cls._fs_factory = classmethod(_fs_factory)

    @classmethod
    def _fs_factory(
        cls, urlpath: str, protocol: str, storage_options: Mapping[str, Any]
    ) -> AbstractFileSystem:
        """Instantiate the filesystem_spec filesystem class"""
        fs_cls = get_filesystem_class(protocol)
        so_dct = fs_cls._get_kwargs_from_urls(urlpath)
        so_dct.update(storage_options)
        return fs_cls(**storage_options)

    @property
    def fs(self) -> AbstractFileSystem:
        try:
            return self._fs_cached
        except AttributeError:
            fs = self._fs_cached = self._fs_factory(
                str(self), self.protocol, self.storage_options
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
    def _url(self):  # todo: deprecate
        return urlsplit(self.as_posix())

    # === pathlib.PurePath ============================================

    def __reduce__(self):
        args = tuple(self._raw_paths)
        kwargs = {
            "protocol": self._protocol,
            **self._storage_options,
        }
        return _make_instance, (type(self), args, kwargs)

    def with_segments(self, *pathsegments):
        return type(self)(
            *pathsegments,
            protocol=self._protocol,
            **self._storage_options,
        )

    @classmethod
    def _parse_path(cls, path):
        if cls._flavour.supports_empty_parts:
            drv, root, rel = cls._flavour.splitroot(path)
            if not root:
                parsed = []
            else:
                parsed = list(map(sys.intern, rel.split(cls._flavour.sep)))
                if parsed[-1] == ".":
                    parsed[-1] = ""
                parsed = [x for x in parsed if x != "."]
            return drv, root, parsed
        return super()._parse_path(path)

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
        if self._flavour.supports_empty_parts and self.parts[-1:] == ("",):
            base = self.with_segments(self.anchor, *self._tail[:-1])
        else:
            base = self
        for name in self.fs.listdir(self.path):
            # fsspec returns dictionaries
            if isinstance(name, dict):
                name = name.get("name")
            if name in {".", ".."}:
                # Yielding a path object for these makes little sense
                continue
            # only want the path name with iterdir
            _, _, name = name.removesuffix("/").rpartition(self._flavour.sep)
            yield base._make_child_relpath(name)

    def _scandir(self):
        raise NotImplementedError  # todo

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
        last_idx = len(resolvable_parts) - 1
        for idx, part in enumerate(resolvable_parts):
            if part == "..":
                if resolved:
                    resolved.pop()
                if self._flavour.supports_empty_parts and idx == last_idx:
                    resolved.append("")
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

    def rename(
        self, target, *, recursive=False, maxdepth=None, **kwargs
    ):  # fixme: non-standard
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
        raise NotImplementedError  # todo

    def symlink_to(self, target, target_is_directory=False):
        raise NotImplementedError

    def hardlink_to(self, target):
        raise NotImplementedError

    def expanduser(self):
        raise NotImplementedError
