from __future__ import annotations

import os
import sys
import warnings
from copy import copy
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING
from typing import Any
from typing import Mapping
from typing import TypeVar
from urllib.parse import urlsplit

from fsspec import AbstractFileSystem
from fsspec import get_filesystem_class

from upath._compat import FSSpecAccessorShim
from upath._compat import PathlibPathShim
from upath._compat import str_remove_prefix
from upath._compat import str_remove_suffix
from upath._flavour import FSSpecFlavour
from upath._protocol import get_upath_protocol
from upath._stat import UPathStatResult
from upath.registry import get_upath_class

__all__ = ["UPath"]


def __getattr__(name):
    if name == "_UriFlavour":
        warnings.warn(
            "upath.core._UriFlavour should not be used anymore."
            " Please follow the universal_pathlib==0.2.0 migration guide at"
            " https://github.com/fsspec/universal_pathlib for more"
            " information.",
            DeprecationWarning,
            stacklevel=2,
        )
        return FSSpecFlavour
    elif name == "PT":
        warnings.warn(
            "upath.core.PT should not be used anymore."
            " Please follow the universal_pathlib==0.2.0 migration guide at"
            " https://github.com/fsspec/universal_pathlib for more"
            " information.",
            DeprecationWarning,
            stacklevel=2,
        )
        return TypeVar("PT", bound="UPath")
    else:
        raise AttributeError(name)


_FSSPEC_HAS_WORKING_GLOB = None


def _check_fsspec_has_working_glob():
    global _FSSPEC_HAS_WORKING_GLOB
    from fsspec.implementations.memory import MemoryFileSystem

    m = type("_M", (MemoryFileSystem,), {"store": {}, "pseudo_dirs": [""]})()
    m.touch("a.txt")
    m.touch("f/b.txt")
    g = _FSSPEC_HAS_WORKING_GLOB = len(m.glob("**/*.txt")) == 2
    return g


def _make_instance(cls, args, kwargs):
    """helper for pickling UPath instances"""
    return cls(*args, **kwargs)


# accessors are deprecated
_FSSpecAccessor = FSSpecAccessorShim


class UPath(PathlibPathShim, Path):
    __slots__ = (
        "_protocol",
        "_storage_options",
        "_fs_cached",
        *PathlibPathShim.__missing_py312_slots__,
        "__drv",
        "__root",
        "__parts",
    )
    if TYPE_CHECKING:
        _protocol: str
        _storage_options: dict[str, Any]
        _fs_cached: AbstractFileSystem

    _protocol_dispatch: bool | None = None
    _flavour = FSSpecFlavour()

    # === upath.UPath constructor =====================================

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

        # determine the protocol
        pth_protocol = get_upath_protocol(
            part0, protocol=protocol, storage_options=storage_options
        )
        # determine which UPath subclass to dispatch to
        if cls._protocol_dispatch or cls._protocol_dispatch is None:
            upath_cls = get_upath_class(protocol=pth_protocol)
            if upath_cls is None:
                raise ValueError(f"Unsupported filesystem: {pth_protocol!r}")
        else:
            # user subclasses can request to disable protocol dispatch
            # by setting MyUPathSubclass._protocol_dispatch to `False`.
            # This will effectively ignore the registered UPath
            # implementations and return an instance of MyUPathSubclass.
            # This can be useful if a subclass wants to extend the UPath
            # api, and it is fine to rely on the default implementation
            # for all supported user protocols.
            upath_cls = cls

        # create a new instance
        if cls is UPath:
            # we called UPath() directly, and want an instance based on the
            # provided or detected protocol (i.e. upath_cls)
            obj: UPath = object.__new__(upath_cls)
            obj._protocol = pth_protocol

        elif issubclass(cls, upath_cls):
            # we called a sub- or sub-sub-class of UPath, i.e. S3Path() and the
            # corresponding upath_cls based on protocol is equal-to or a
            # parent-of the cls.
            obj = object.__new__(cls)
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

            obj = object.__new__(upath_cls)
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
        # allow subclasses to customize __init__ arg parsing
        base_options = getattr(self, "_storage_options", {})
        args, protocol, storage_options = type(self)._transform_init_args(
            args, protocol or self._protocol, {**base_options, **storage_options}
        )
        if self._protocol != protocol and protocol:
            self._protocol = protocol

        # retrieve storage_options
        if args:
            args0 = args[0]
            if isinstance(args0, UPath):
                self._storage_options = {**args0.storage_options, **storage_options}
            else:
                self._storage_options = type(self)._parse_storage_options(
                    str(args0), protocol, storage_options
                )
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
                # TODO:
                #   Future versions of UPath could verify that storage_options
                #   can be combined between UPath instances. Not sure if this
                #   is really necessary though. A warning might be enough...
                pass

        # fill ._raw_paths
        if hasattr(self, "_raw_paths"):
            return
        super().__init__(*args)

    # === upath.UPath PUBLIC ADDITIONAL API ===========================

    @property
    def protocol(self) -> str:
        return self._protocol

    @property
    def storage_options(self) -> Mapping[str, Any]:
        return MappingProxyType(self._storage_options)

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

    # === upath.UPath CUSTOMIZABLE API ================================

    @classmethod
    def _transform_init_args(
        cls,
        args: tuple[str | os.PathLike, ...],
        protocol: str,
        storage_options: dict[str, Any],
    ) -> tuple[tuple[str | os.PathLike, ...], str, dict[str, Any]]:
        """allow customization of init args in subclasses"""
        return args, protocol, storage_options

    @classmethod
    def _parse_storage_options(
        cls, urlpath: str, protocol: str, storage_options: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Parse storage_options from the urlpath"""
        fs_cls: type[AbstractFileSystem] = get_filesystem_class(protocol)
        pth_storage_options = fs_cls._get_kwargs_from_urls(urlpath)
        return {**pth_storage_options, **storage_options}

    @classmethod
    def _fs_factory(
        cls, urlpath: str, protocol: str, storage_options: Mapping[str, Any]
    ) -> AbstractFileSystem:
        """Instantiate the filesystem_spec filesystem class"""
        fs_cls = get_filesystem_class(protocol)
        so_dct = fs_cls._get_kwargs_from_urls(urlpath)
        so_dct.update(storage_options)
        return fs_cls(**storage_options)

    # === upath.UPath COMPATIBILITY API ===============================

    def __init_subclass__(cls, **kwargs):
        """provide a clean migration path for custom user subclasses"""

        # Check if the user subclass has a custom `__new__` method
        has_custom_new_method = cls.__new__ is not UPath.__new__

        if has_custom_new_method and cls._protocol_dispatch is None:
            warnings.warn(
                "Detected a customized `__new__` method in subclass"
                f" {cls.__name__!r}. Protocol dispatch will be disabled"
                " for this subclass. Please follow the"
                " universal_pathlib==0.2.0 migration guide at"
                " https://github.com/fsspec/universal_pathlib for more"
                " information.",
                DeprecationWarning,
                stacklevel=2,
            )
            cls._protocol_dispatch = False

        # Check if the user subclass has defined a custom accessor class
        accessor_cls = getattr(cls, "_default_accessor", None)

        has_custom_legacy_accessor = (
            accessor_cls is not None
            and issubclass(accessor_cls, FSSpecAccessorShim)
            and accessor_cls is not FSSpecAccessorShim
        )
        has_customized_fs_instantiation = (
            accessor_cls.__init__ is not FSSpecAccessorShim.__init__
            or hasattr(accessor_cls, "_fs")
        )

        if has_custom_legacy_accessor and has_customized_fs_instantiation:
            warnings.warn(
                "Detected a customized `__init__` method or `_fs` attribute"
                f" in the provided `_FSSpecAccessor` subclass of {cls.__name__!r}."
                " It is recommended to instead override the `UPath._fs_factory`"
                " classmethod to customize filesystem instantiation. Please follow"
                " the universal_pathlib==0.2.0 migration guide at"
                " https://github.com/fsspec/universal_pathlib for more"
                " information.",
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

            def _parse_storage_options(
                cls_, urlpath: str, protocol: str, storage_options: Mapping[str, Any]
            ) -> dict[str, Any]:
                url = urlsplit(urlpath)
                if protocol:
                    url = url._replace(scheme=protocol)
                inst = cls_._default_accessor(url, **storage_options)
                return inst._fs.storage_options

            cls._fs_factory = classmethod(_fs_factory)
            cls._parse_storage_options = classmethod(_parse_storage_options)

    @property
    def _path(self):
        warnings.warn(
            "UPath._path is deprecated and should not be used."
            " Please follow the universal_pathlib==0.2.0 migration guide at"
            " https://github.com/fsspec/universal_pathlib for more"
            " information.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.path

    @property
    def _kwargs(self):
        warnings.warn(
            "UPath._kwargs is deprecated. Please use"
            " UPath.storage_options instead. Follow the"
            " universal_pathlib==0.2.0 migration guide at"
            " https://github.com/fsspec/universal_pathlib for more"
            " information.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.storage_options

    @property
    def _url(self):
        # TODO:
        #   _url should be deprecated, but for now there is no good way of
        #   accessing query parameters from urlpaths...
        return urlsplit(self.as_posix())

    def __getattr__(self, item):
        if item == "_accessor":
            warnings.warn(
                "UPath._accessor is deprecated. Please use"
                " UPath.fs instead. Follow the"
                " universal_pathlib==0.2.0 migration guide at"
                " https://github.com/fsspec/universal_pathlib for more"
                " information.",
                DeprecationWarning,
                stacklevel=2,
            )
            if hasattr(self, "_default_accessor"):
                accessor_cls = self._default_accessor
            else:
                accessor_cls = FSSpecAccessorShim
            return accessor_cls.from_path(self)
        else:
            raise AttributeError(item)

    @classmethod
    def _from_parts(cls, parts, **kwargs):
        warnings.warn(
            "UPath._from_parts is deprecated and should not be used."
            " Please follow the universal_pathlib==0.2.0 migration guide at"
            " https://github.com/fsspec/universal_pathlib for more"
            " information.",
            DeprecationWarning,
            stacklevel=2,
        )
        parsed_url = kwargs.pop("url", None)
        if parsed_url:
            if protocol := parsed_url.scheme:
                kwargs["protocol"] = protocol
            if netloc := parsed_url.netloc:
                kwargs["netloc"] = netloc
        obj = UPath.__new__(cls, parts, **kwargs)
        obj.__init__(*parts, **kwargs)
        return obj

    @classmethod
    def _parse_args(cls, args):
        warnings.warn(
            "UPath._parse_args is deprecated and should not be used."
            " Please follow the universal_pathlib==0.2.0 migration guide at"
            " https://github.com/fsspec/universal_pathlib for more"
            " information.",
            DeprecationWarning,
            stacklevel=2,
        )
        pth = cls._flavour.join(*args)
        return cls._parse_path(pth)

    @classmethod
    def _format_parsed_parts(cls, drv, root, tail, **kwargs):
        if kwargs:
            warnings.warn(
                "UPath._format_parsed_parts should not be used with"
                " additional kwargs. Please follow the"
                " universal_pathlib==0.2.0 migration guide at"
                " https://github.com/fsspec/universal_pathlib for more"
                " information.",
                DeprecationWarning,
                stacklevel=2,
            )
            if "url" in kwargs and tail[:1] == [f"{drv}{root}"]:
                # This was called from code that expected py38-py311 behavior
                # of _format_parsed_parts, which takes drv, root and parts
                tail = tail[1:]
        return super()._format_parsed_parts(drv, root, tail)

    @property
    def _drv(self):
        # direct access to ._drv should emit a warning,
        # but there is no good way of doing this for now...
        try:
            return self.__drv
        except AttributeError:
            self._load_parts()
            return self.__drv

    @_drv.setter
    def _drv(self, value):
        self.__drv = value

    @property
    def _root(self):
        # direct access to ._root should emit a warning,
        # but there is no good way of doing this for now...
        try:
            return self.__root
        except AttributeError:
            self._load_parts()
            return self.__root

    @_root.setter
    def _root(self, value):
        self.__root = value

    @property
    def _parts(self):
        # UPath._parts is not used anymore, and not available
        # in pathlib.Path for Python 3.12 and later.
        # Direct access to ._parts should emit a deprecation warning,
        # but there is no good way of doing this for now...
        try:
            return self.__parts
        except AttributeError:
            self._load_parts()
            self.__parts = super().parts
            return list(self.__parts)

    @_parts.setter
    def _parts(self, value):
        self.__parts = value

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
        if getattr(cls._flavour, "supports_empty_parts", False):
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

    def __eq__(self, other):
        if not isinstance(other, UPath):
            return NotImplemented
        return (
            self.path == other.path
            and self.storage_options == other.storage_options
            and (
                get_filesystem_class(self.protocol)
                == get_filesystem_class(other.protocol)
            )
        )

    def __hash__(self):
        return hash((self.path, self.storage_options, self.protocol))

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

    def stat(self, *, follow_symlinks=True) -> UPathStatResult:
        if not follow_symlinks:
            warnings.warn(
                "UPath.stat(follow_symlinks=False): follow_symlinks=False is"
                " currently ignored.",
                UserWarning,
                stacklevel=2,
            )
        return UPathStatResult.from_info(self.fs.stat(self.path))

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
        if getattr(self._flavour, "supports_empty_parts", False) and self.parts[
            -1:
        ] == ("",):
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
            _, _, name = str_remove_suffix(name, "/").rpartition(self._flavour.sep)
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
            name = str_remove_prefix(str_remove_prefix(name, self.path), sep)
            yield self.joinpath(name)

    def rglob(self, pattern: str, *, case_sensitive=None):
        if _FSSPEC_HAS_WORKING_GLOB is None:
            _check_fsspec_has_working_glob()

        if _FSSPEC_HAS_WORKING_GLOB:
            r_path_pattern = self.joinpath("**", pattern).path
            sep = self._flavour.sep
            for name in self.fs.glob(r_path_pattern):
                name = str_remove_prefix(str_remove_prefix(name, self.path), sep)
                yield self.joinpath(name)

        else:
            path_pattern = self.joinpath(pattern).path
            r_path_pattern = self.joinpath("**", pattern).path
            sep = self._flavour.sep
            seen = set()
            for p in (path_pattern, r_path_pattern):
                for name in self.fs.glob(p):
                    name = str_remove_prefix(str_remove_prefix(name, self.path), sep)
                    if name in seen:
                        continue
                    else:
                        seen.add(name)
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

    def absolute(self):
        return self

    def resolve(self, strict: bool = False):
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
                if (
                    getattr(self._flavour, "supports_empty_parts", False)
                    and idx == last_idx
                ):
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
        if parents and not exist_ok and self.exists():
            raise FileExistsError(str(self))
        try:
            self.fs.mkdir(
                self.path,
                create_parents=parents,
                mode=mode,
            )
        except FileExistsError:
            if not exist_ok:
                raise FileExistsError(str(self))
            if not self.is_dir():
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
