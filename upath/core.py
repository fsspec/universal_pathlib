from __future__ import annotations

import posixpath
import sys
import warnings
from abc import ABCMeta
from abc import abstractmethod
from collections.abc import Iterator
from collections.abc import Mapping
from collections.abc import Sequence
from copy import copy
from types import MappingProxyType
from typing import IO
from typing import TYPE_CHECKING
from typing import Any
from typing import BinaryIO
from typing import Literal
from typing import NoReturn
from typing import TextIO
from typing import TypeVar
from typing import overload
from urllib.parse import SplitResult
from urllib.parse import urlsplit

from fsspec.registry import get_filesystem_class
from fsspec.spec import AbstractFileSystem

from upath._chain import DEFAULT_CHAIN_PARSER
from upath._chain import Chain
from upath._chain import FSSpecChainParser
from upath._flavour import LazyFlavourDescriptor
from upath._flavour import WrappedFileSystemFlavour
from upath._flavour import upath_get_kwargs_from_url
from upath._flavour import upath_urijoin
from upath._info import UPathInfo
from upath._protocol import compatible_protocol
from upath._protocol import get_upath_protocol
from upath._stat import UPathStatResult
from upath.registry import get_upath_class
from upath.types import UNSET_DEFAULT
from upath.types import JoinablePathLike
from upath.types import PathInfo
from upath.types import ReadablePath
from upath.types import ReadablePathLike
from upath.types import SupportsPathLike
from upath.types import UPathParser
from upath.types import WritablePath
from upath.types import WritablePathLike

if TYPE_CHECKING:
    import upath.implementations as _uimpl

    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self

    from pydantic import GetCoreSchemaHandler
    from pydantic_core.core_schema import CoreSchema

    _MT = TypeVar("_MT")
    _WT = TypeVar("_WT", bound="WritablePath")

__all__ = ["UPath"]

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
    # Extract _relative_base if present
    relative_base = kwargs.pop("_relative_base", None)
    instance = cls(*args, **kwargs)
    if relative_base is not None:
        instance._relative_base = relative_base
    return instance


def _buffering2blocksize(mode: str, buffering: int) -> int | None:
    if not isinstance(buffering, int):
        raise TypeError("buffering must be an integer")
    if buffering == 0:  # buffering disabled
        if "b" not in mode:  # text mode
            raise ValueError("can't have unbuffered text I/O")
        return buffering
    elif buffering == -1:
        return None
    else:
        return buffering


def _raise_unsupported(cls_name: str, method: str) -> NoReturn:
    "relative path does not support method(), because cls_name.cwd() is unsupported"
    raise NotImplementedError(f"{cls_name}.{method}() is unsupported")


class _UPathMeta(ABCMeta):
    if sys.version_info < (3, 11):
        # pathlib 3.9 and 3.10 supported `Path[str]` but
        # did not return a GenericAlias but the class itself?
        def __getitem__(cls, key):
            return cls

    def __call__(cls: type[_MT], *args: Any, **kwargs: Any) -> _MT:
        # create a copy if UPath class
        try:
            (arg0,) = args
        except ValueError:
            pass
        else:
            if isinstance(arg0, UPath) and not kwargs:
                return copy(arg0)  # type: ignore[return-value]
        # We do this call manually, because cls could be a registered
        # subclass of UPath that is not directly inheriting from UPath.
        inst = cls.__new__(cls, *args, **kwargs)
        inst.__init__(*args, **kwargs)  # type: ignore[misc]
        return inst


class _UPathMixin(metaclass=_UPathMeta):
    __slots__ = ()

    @property
    @abstractmethod
    def parser(self) -> UPathParser:
        raise NotImplementedError

    @property
    def _protocol(self) -> str:
        return self._chain.nest().protocol

    @_protocol.setter
    def _protocol(self, value: str) -> None:
        self._chain = self._chain.replace(protocol=value)

    @property
    def _storage_options(self) -> dict[str, Any]:
        return self._chain.nest().storage_options

    @_storage_options.setter
    def _storage_options(self, value: dict[str, Any]) -> None:
        self._chain = self._chain.replace(storage_options=value)

    @property
    @abstractmethod
    def _chain(self) -> Chain:
        raise NotImplementedError

    @_chain.setter
    @abstractmethod
    def _chain(self, value: Chain) -> None:
        raise NotImplementedError

    @property
    @abstractmethod
    def _chain_parser(self) -> FSSpecChainParser:
        raise NotImplementedError

    @_chain_parser.setter
    @abstractmethod
    def _chain_parser(self, value: FSSpecChainParser) -> None:
        raise NotImplementedError

    @property
    @abstractmethod
    def _fs_cached(self) -> AbstractFileSystem:
        raise NotImplementedError

    @_fs_cached.setter
    def _fs_cached(self, value: AbstractFileSystem):
        raise NotImplementedError

    @property
    @abstractmethod
    def _raw_urlpaths(self) -> Sequence[JoinablePathLike]:
        raise NotImplementedError

    @_raw_urlpaths.setter
    def _raw_urlpaths(self, value: Sequence[JoinablePathLike]) -> None:
        raise NotImplementedError

    @property
    @abstractmethod
    def _relative_base(self) -> str | None:
        raise NotImplementedError

    @_relative_base.setter
    def _relative_base(self, value: str | None) -> None:
        raise NotImplementedError

    # === upath.UPath PUBLIC ADDITIONAL API ===========================

    @property
    def protocol(self) -> str:
        """The fsspec protocol for the path."""
        return self._protocol

    @property
    def storage_options(self) -> Mapping[str, Any]:
        """The fsspec storage options for the path."""
        return MappingProxyType(self._storage_options)

    @property
    def fs(self) -> AbstractFileSystem:
        """The cached fsspec filesystem instance for the path."""
        try:
            return self._fs_cached
        except AttributeError:
            fs = self._fs_cached = self._fs_factory(
                str(self), self.protocol, self.storage_options
            )
            return fs

    @property
    def path(self) -> str:
        """The path that a fsspec filesystem can use."""
        if self._relative_base is not None:
            try:
                # For relative paths, we need to resolve to absolute path
                current_dir = self.cwd()  # type: ignore[attr-defined]
            except NotImplementedError:
                raise NotImplementedError(
                    f"fsspec paths can not be relative and"
                    f" {type(self).__name__}.cwd() is unsupported"
                ) from None
            # Join the current directory with the relative path
            if (self_path := str(self)) == ".":
                path = str(current_dir)
            else:
                path = current_dir.parser.join(str(self), self_path)
            return self.parser.strip_protocol(path)
        return self._chain.active_path

    def joinuri(self, uri: JoinablePathLike) -> UPath:
        """Join with urljoin behavior for UPath instances"""
        # short circuit if the new uri uses a different protocol
        other_protocol = get_upath_protocol(uri)
        if other_protocol and other_protocol != self._protocol:
            return UPath(uri)
        return UPath(
            upath_urijoin(str(self), str(uri)),
            protocol=other_protocol or self._protocol,
            **self.storage_options,
        )

    # === upath.UPath CUSTOMIZABLE API ================================

    @classmethod
    def _transform_init_args(
        cls,
        args: tuple[JoinablePathLike, ...],
        protocol: str,
        storage_options: dict[str, Any],
    ) -> tuple[tuple[JoinablePathLike, ...], str, dict[str, Any]]:
        """allow customization of init args in subclasses"""
        return args, protocol, storage_options

    @classmethod
    def _parse_storage_options(
        cls,
        urlpath: str,
        protocol: str,
        storage_options: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Parse storage_options from the urlpath"""
        pth_storage_options = upath_get_kwargs_from_url(urlpath)
        return {**pth_storage_options, **storage_options}

    @classmethod
    def _fs_factory(
        cls,
        urlpath: str,
        protocol: str,
        storage_options: Mapping[str, Any],
    ) -> AbstractFileSystem:
        """Instantiate the filesystem_spec filesystem class"""
        fs_cls = get_filesystem_class(protocol)
        so_dct = fs_cls._get_kwargs_from_urls(urlpath)
        so_dct.update(storage_options)
        return fs_cls(**storage_options)

    # === upath.UPath constructor =====================================

    _protocol_dispatch: bool | None = None

    def __new__(
        cls,
        *args: JoinablePathLike,
        protocol: str | None = None,
        chain_parser: FSSpecChainParser = DEFAULT_CHAIN_PARSER,
        **storage_options: Any,
    ) -> UPath:
        # narrow type
        if not issubclass(cls, UPath):
            raise TypeError("UPath.__new__ can't instantiate non-UPath classes")

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
            args[0] if args else "",
            protocol=protocol,
            storage_options=storage_options,
        )
        # determine which UPath subclass to dispatch to
        upath_cls: type[UPath] | None
        if cls._protocol_dispatch or cls._protocol_dispatch is None:
            upath_cls = get_upath_class(protocol=pth_protocol)
            if upath_cls is None:
                raise ValueError(f"Unsupported filesystem: {pth_protocol!r}")
        else:
            # user subclasses can request to disable protocol dispatch
            # by setting MyUPathSubclass._protocol_dispatch to `False`.
            # This will effectively ignore the registered UPath
            # implementations and return an instance of MyUPathSubclass.
            # This be useful if a subclass wants to extend the UPath
            # api, and it is fine to rely on the default implementation
            # for all supported user protocols.
            #
            # THIS IS DEPRECATED!
            # Use upath.extensions.ProxyUPath to extend the UPath API
            warnings.warn(
                f"{cls.__name__}._protocol_dispatch = False is deprecated and"
                " will be removed in future universal_pathlib versions."
                " To extend the UPath API, subclass upath.extensions.ProxyUPath",
                DeprecationWarning,
                stacklevel=2,
            )
            upath_cls = cls

        if issubclass(upath_cls, cls):
            pass

        elif not issubclass(upath_cls, UPath):
            raise RuntimeError("UPath.__new__ expected cls to be subclass of UPath")

        else:
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
            warnings.warn(
                msg,
                DeprecationWarning,
                stacklevel=2,
            )
            upath_cls = cls

        return object.__new__(upath_cls)

    def __init__(
        self,
        *args: JoinablePathLike,
        protocol: str | None = None,
        chain_parser: FSSpecChainParser = DEFAULT_CHAIN_PARSER,
        **storage_options: Any,
    ) -> None:

        # todo: avoid duplicating this call from __new__
        protocol = get_upath_protocol(
            args[0] if args else "",
            protocol=protocol,
            storage_options=storage_options,
        )
        args, protocol, storage_options = type(self)._transform_init_args(
            args, protocol, storage_options
        )

        # check that UPath subclasses in args are compatible
        # TODO:
        #   Future versions of UPath could verify that storage_options
        #   can be combined between UPath instances. Not sure if this
        #   is really necessary though. A warning might be enough...
        if not compatible_protocol(protocol, *args):
            raise ValueError("can't combine incompatible UPath protocols")

        if args:
            args0 = args[0]
            if isinstance(args0, UPath):
                storage_options = {
                    **args0._chain.nest().storage_options,
                    **storage_options,
                }
                str_args0 = args0.__vfspath__()

            else:
                if hasattr(args0, "__fspath__") and args0.__fspath__ is not None:
                    str_args0 = args0.__fspath__()
                elif hasattr(args0, "__vfspath__") and args0.__vfspath__ is not None:
                    str_args0 = args0.__vfspath__()
                elif isinstance(args0, str):
                    str_args0 = args0
                else:
                    raise TypeError(
                        "argument should be a UPath, str, "
                        f"or support __vfspath__ or __fspath__, not {type(args0)!r}"
                    )
                storage_options = type(self)._parse_storage_options(
                    str_args0, protocol, storage_options
                )
        else:
            str_args0 = "."

        segments = chain_parser.unchain(
            str_args0,
            protocol=protocol,
            storage_options=storage_options,
        )
        # FIXME: normalization needs to happen in unchain already...
        chain = Chain.from_list(Chain.from_list(segments).to_list())
        if len(args) > 1:
            chain = chain.replace(
                path=WrappedFileSystemFlavour.from_protocol(protocol).join(
                    chain.active_path,
                    *args[1:],
                )
            )
        self._chain = chain
        self._chain_parser = chain_parser
        self._raw_urlpaths = args
        self._relative_base = None

    # --- deprecated attributes ---------------------------------------

    @property
    def _url(self) -> SplitResult:
        # TODO:
        #   _url should be deprecated, but for now there is no good way of
        #   accessing query parameters from urlpaths...
        return urlsplit(self.__str__())


class UPath(_UPathMixin, WritablePath, ReadablePath):
    __slots__ = (
        "_chain",
        "_chain_parser",
        "_fs_cached",
        "_raw_urlpaths",
        "_relative_base",
    )

    if TYPE_CHECKING:  # noqa: C901
        _chain: Chain
        _chain_parser: FSSpecChainParser
        _fs_cached: bool
        _raw_urlpaths: Sequence[JoinablePathLike]
        _relative_base: str | None

        @overload
        def __new__(
            cls,
        ) -> Self: ...
        @overload  # noqa: E301
        def __new__(
            cls,
            *args: JoinablePathLike,
            protocol: Literal["simplecache"],
            **_: Any,
        ) -> _uimpl.cached.SimpleCachePath: ...
        @overload  # noqa: E301
        def __new__(
            cls,
            *args: JoinablePathLike,
            protocol: Literal["gcs", "gs"],
            **_: Any,
        ) -> _uimpl.cloud.GCSPath: ...
        @overload  # noqa: E301
        def __new__(
            cls,
            *args: JoinablePathLike,
            protocol: Literal["s3", "s3a"],
            **_: Any,
        ) -> _uimpl.cloud.S3Path: ...
        @overload  # noqa: E301
        def __new__(
            cls,
            *args: JoinablePathLike,
            protocol: Literal["az", "abfs", "abfss", "adl"],
            **_: Any,
        ) -> _uimpl.cloud.AzurePath: ...
        @overload  # noqa: E301
        def __new__(
            cls,
            *args: JoinablePathLike,
            protocol: Literal["data"],
            **_: Any,
        ) -> _uimpl.data.DataPath: ...
        @overload  # noqa: E301
        def __new__(
            cls,
            *args: JoinablePathLike,
            protocol: Literal["github"],
            **_: Any,
        ) -> _uimpl.github.GitHubPath: ...
        @overload  # noqa: E301
        def __new__(
            cls,
            *args: JoinablePathLike,
            protocol: Literal["hdfs"],
            **_: Any,
        ) -> _uimpl.hdfs.HDFSPath: ...
        @overload  # noqa: E301
        def __new__(
            cls,
            *args: JoinablePathLike,
            protocol: Literal["http", "https"],
            **_: Any,
        ) -> _uimpl.http.HTTPPath: ...
        @overload  # noqa: E301
        def __new__(
            cls,
            *args: JoinablePathLike,
            protocol: Literal["file", "local"],
            **_: Any,
        ) -> _uimpl.local.FilePath: ...
        @overload  # noqa: E301
        def __new__(
            cls,
            *args: JoinablePathLike,
            protocol: Literal["memory"],
            **_: Any,
        ) -> _uimpl.memory.MemoryPath: ...
        @overload  # noqa: E301
        def __new__(
            cls,
            *args: JoinablePathLike,
            protocol: Literal["sftp", "ssh"],
            **_: Any,
        ) -> _uimpl.sftp.SFTPPath: ...
        @overload  # noqa: E301
        def __new__(
            cls,
            *args: JoinablePathLike,
            protocol: Literal["smb"],
            **_: Any,
        ) -> _uimpl.smb.SMBPath: ...
        @overload  # noqa: E301
        def __new__(
            cls,
            *args: JoinablePathLike,
            protocol: Literal["tar"],
            **_: Any,
        ) -> _uimpl.tar.TarPath: ...
        @overload  # noqa: E301
        def __new__(
            cls,
            *args: JoinablePathLike,
            protocol: Literal["webdav"],
            **_: Any,
        ) -> _uimpl.webdav.WebdavPath: ...
        @overload  # noqa: E301
        def __new__(
            cls,
            *args: JoinablePathLike,
            protocol: Literal["zip"],
            **_: Any,
        ) -> _uimpl.zip.ZipPath: ...

        if sys.platform == "win32":

            @overload  # noqa: E301
            def __new__(
                cls,
                *args: JoinablePathLike,
                protocol: Literal[""],
                **_: Any,
            ) -> _uimpl.local.WindowsUPath: ...

        else:

            @overload  # noqa: E301
            def __new__(
                cls,
                *args: JoinablePathLike,
                protocol: Literal[""],
                **_: Any,
            ) -> _uimpl.local.PosixUPath: ...

        @overload  # noqa: E301
        def __new__(
            cls,
            *args: JoinablePathLike,
            protocol: str | None = ...,
            **_: Any,
        ) -> Self: ...

        def __new__(
            cls,
            *args: JoinablePathLike,
            protocol: str | None = ...,
            chain_parser: FSSpecChainParser = ...,
            **storage_options: Any,
        ) -> Self: ...

    # === JoinablePath attributes =====================================

    parser: UPathParser = LazyFlavourDescriptor()  # type: ignore[assignment]

    def with_segments(self, *pathsegments: JoinablePathLike) -> Self:
        # we change joinpath behavior if called from a relative path
        # this is not fully ideal, but currently the best way to move forward
        if is_relative := self._relative_base is not None:
            pathsegments = (self._relative_base, *pathsegments)

        new_instance = type(self)(
            *pathsegments,
            protocol=self._protocol,
            **self._storage_options,
        )

        if is_relative:
            new_instance._relative_base = self._relative_base
        return new_instance

    def __str__(self) -> str:
        if self._relative_base is not None:
            active_path = self._chain.active_path
            stripped_base = self.parser.strip_protocol(
                self._relative_base
            ).removesuffix(self.parser.sep)
            if not active_path.startswith(stripped_base):
                raise RuntimeError(
                    f"{active_path!r} is not a subpath of {stripped_base!r}"
                )

            return (
                active_path.removeprefix(stripped_base).removeprefix(self.parser.sep)
                or "."
            )
        else:
            return self._chain_parser.chain(self._chain.to_list())[0]

    def __vfspath__(self) -> str:
        if self._relative_base is not None:
            return self.__str__()
        else:
            return self.path

    def __repr__(self) -> str:
        cls_name = type(self).__name__
        path = self.__vfspath__()
        if self._relative_base is not None:
            return f"<relative {cls_name} {path!r}>"
        else:
            return f"{cls_name}({path!r}, protocol={self._protocol!r})"

    # === JoinablePath overrides ======================================

    @property
    def parts(self) -> Sequence[str]:
        # For relative paths, return parts of the relative path only
        if self._relative_base is not None:
            rel_str = str(self)
            if rel_str == ".":
                return ()
            return tuple(rel_str.split(self.parser.sep))

        split = self.parser.split
        sep = self.parser.sep

        path = self._chain.active_path
        drive = self.parser.splitdrive(self._chain.active_path)[0]
        stripped_path = self.parser.strip_protocol(path)
        if stripped_path:
            _, _, tail = path.partition(stripped_path)
            path = stripped_path + tail

        parent, name = split(path)
        names = []
        while path != parent:
            names.append(name)
            path = parent
            parent, name = split(path)

        if names and names[-1] == drive:
            names = names[:-1]
        if names and names[-1].startswith(sep):
            parts = [*names[:-1], names[-1].removeprefix(sep), drive + sep]
        else:
            parts = [*names, drive + sep]
        return tuple(reversed(parts))

    def with_name(self, name: str) -> Self:
        """Return a new path with the file name changed."""
        split = self.parser.split
        if self.parser.sep in name:  # `split(name)[0]`
            raise ValueError(f"Invalid name {name!r}")
        _path = self.__vfspath__()
        _path = _path.removesuffix(split(_path)[1]) + name
        return self.with_segments(_path)

    @property
    def anchor(self) -> str:
        if self._relative_base is not None:
            return ""
        return self.drive + self.root

    @property
    def parent(self) -> Self:
        if self._relative_base is not None:
            if str(self) == ".":
                return self
            else:
                # this needs to be revisited...
                pth = type(self)(
                    self._relative_base,
                    str(self),
                    protocol=self._protocol,
                    **self._storage_options,
                )
                parent = pth.parent
                parent._relative_base = self._relative_base
                return parent
        return super().parent

    @property
    def parents(self) -> Sequence[Self]:
        if self._relative_base is not None:
            parents = []
            parent = self
            while True:
                if str(parent) == ".":
                    break
                parent = parent.parent
                parents.append(parent)
            return parents
        return super().parents

    def joinpath(self, *pathsegments: JoinablePathLike) -> Self:
        return self.with_segments(self.__vfspath__(), *pathsegments)

    def __truediv__(self, key: JoinablePathLike) -> Self:
        try:
            return self.with_segments(self.__vfspath__(), key)
        except TypeError:
            return NotImplemented

    def __rtruediv__(self, key: JoinablePathLike) -> Self:
        try:
            return self.with_segments(key, self.__vfspath__())
        except TypeError:
            return NotImplemented

    # === ReadablePath attributes =====================================

    @property
    def info(self) -> PathInfo:
        return UPathInfo(self)

    def iterdir(self) -> Iterator[Self]:
        sep = self.parser.sep
        base = self
        if self.parts[-1:] == ("",):
            base = self.parent
        for name in base.fs.listdir(base.path):
            # fsspec returns dictionaries
            if isinstance(name, dict):
                name = name.get("name")
            if name in {".", ".."}:
                # Yielding a path object for these makes little sense
                continue
            # only want the path name with iterdir
            _, _, name = name.removesuffix(sep).rpartition(self.parser.sep)
            yield base.with_segments(base.path, name)

    def __open_reader__(self) -> BinaryIO:
        return self.fs.open(self.path, mode="rb")

    if sys.version_info >= (3, 14):

        def __open_rb__(self, buffering: int = UNSET_DEFAULT) -> BinaryIO:
            return self.open("rb", buffering=buffering)

    def readlink(self) -> Self:
        _raise_unsupported(type(self).__name__, "readlink")

    @overload
    def copy(self, target: _WT, **kwargs: Any) -> _WT: ...

    @overload
    def copy(self, target: SupportsPathLike | str, **kwargs: Any) -> Self: ...

    def copy(self, target: _WT | SupportsPathLike | str, **kwargs: Any) -> _WT | UPath:
        if not isinstance(target, UPath):
            return super().copy(self.with_segments(target), **kwargs)
        else:
            return super().copy(target, **kwargs)

    @overload
    def copy_into(self, target_dir: _WT, **kwargs: Any) -> _WT: ...

    @overload
    def copy_into(self, target_dir: SupportsPathLike | str, **kwargs: Any) -> Self: ...

    def copy_into(
        self, target_dir: _WT | SupportsPathLike | str, **kwargs: Any
    ) -> _WT | UPath:
        if not isinstance(target_dir, UPath):
            return super().copy_into(self.with_segments(target_dir), **kwargs)
        else:
            return super().copy_into(target_dir, **kwargs)

    @overload
    def move(self, target: _WT, **kwargs: Any) -> _WT: ...

    @overload
    def move(self, target: SupportsPathLike | str, **kwargs: Any) -> Self: ...

    def move(self, target: _WT | SupportsPathLike | str, **kwargs: Any) -> _WT | UPath:
        target = self.copy(target, **kwargs)
        self.fs.rm(self.path, recursive=self.is_dir())
        return target

    @overload
    def move_into(self, target_dir: _WT, **kwargs: Any) -> _WT: ...

    @overload
    def move_into(self, target_dir: SupportsPathLike | str, **kwargs: Any) -> Self: ...

    def move_into(
        self, target_dir: _WT | SupportsPathLike | str, **kwargs: Any
    ) -> _WT | UPath:
        name = self.name
        if not name:
            raise ValueError(f"{self!r} has an empty name")
        elif hasattr(target_dir, "with_segments"):
            target = target_dir.with_segments(target_dir, name)  # type: ignore
        else:
            target = self.with_segments(target_dir, name)
        return self.move(target)

    # --- WritablePath attributes -------------------------------------

    def symlink_to(
        self,
        target: ReadablePathLike,
        target_is_directory: bool = False,
    ) -> None:
        _raise_unsupported(type(self).__name__, "symlink_to")

    def mkdir(
        self,
        mode: int = 0o777,
        parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
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

    def __open_writer__(self, mode: Literal["a", "w", "x"]) -> BinaryIO:
        return self.fs.open(self.path, mode=f"{mode}b")

    # --- upath overrides ---------------------------------------------

    @overload
    def open(
        self,
        mode: Literal["r", "w", "a"] = ...,
        buffering: int = ...,
        encoding: str = ...,
        errors: str = ...,
        newline: str = ...,
        **fsspec_kwargs: Any,
    ) -> TextIO: ...

    @overload
    def open(
        self,
        mode: Literal["rb", "wb", "ab"] = ...,
        buffering: int = ...,
        encoding: str = ...,
        errors: str = ...,
        newline: str = ...,
        **fsspec_kwargs: Any,
    ) -> BinaryIO: ...

    @overload
    def open(
        self,
        mode: str = ...,
        buffering: int = ...,
        encoding: str | None = ...,
        errors: str | None = ...,
        newline: str | None = ...,
        **fsspec_kwargs: Any,
    ) -> IO[Any]: ...

    def open(
        self,
        mode: str = "r",
        buffering: int = UNSET_DEFAULT,
        encoding: str | None = UNSET_DEFAULT,
        errors: str | None = UNSET_DEFAULT,
        newline: str | None = UNSET_DEFAULT,
        **fsspec_kwargs: Any,
    ) -> IO[Any]:
        """
        Open the file pointed by this path and return a file object, as
        the built-in open() function does.

        Parameters
        ----------
        mode:
            Opening mode. Default is 'r'.
        buffering:
            Default is the block size of the underlying fsspec filesystem.
        encoding:
            Encoding is only used in text mode. Default is None.
        errors:
            Error handling for encoding. Only used in text mode. Default is None.
        newline:
            Newline handling. Only used in text mode. Default is None.
        **fsspec_kwargs:
            Additional options for the fsspec filesystem.
        """
        # match the signature of pathlib.Path.open()
        if buffering is not UNSET_DEFAULT:
            if "block_size" in fsspec_kwargs:
                raise TypeError("cannot specify both 'buffering' and 'block_size'")
            block_size = _buffering2blocksize(mode, buffering)
            if block_size is not None:
                fsspec_kwargs.setdefault("block_size", block_size)
        if encoding is not UNSET_DEFAULT:
            fsspec_kwargs["encoding"] = encoding
        if errors is not UNSET_DEFAULT:
            fsspec_kwargs["errors"] = errors
        if newline is not UNSET_DEFAULT:
            fsspec_kwargs["newline"] = newline
        return self.fs.open(self.path, mode=mode, **fsspec_kwargs)

    # === pathlib.Path ================================================

    def stat(
        self,
        *,
        follow_symlinks: bool = True,
    ) -> UPathStatResult:
        if not follow_symlinks:
            warnings.warn(
                f"{type(self).__name__}.stat(follow_symlinks=False):"
                " is currently ignored.",
                UserWarning,
                stacklevel=2,
            )
        return UPathStatResult.from_info(self.fs.info(self.path))

    def lstat(self) -> UPathStatResult:
        return self.stat(follow_symlinks=False)

    def chmod(self, mode: int, *, follow_symlinks: bool = True) -> None:
        _raise_unsupported(type(self).__name__, "chmod")

    def exists(self, *, follow_symlinks: bool = True) -> bool:
        return self.fs.exists(self.path)

    def is_dir(self) -> bool:
        return self.fs.isdir(self.path)

    def is_file(self) -> bool:
        return self.fs.isfile(self.path)

    def is_mount(self) -> bool:
        return False

    def is_symlink(self) -> bool:
        try:
            info = self.fs.info(self.path)
            if "islink" in info:
                return bool(info["islink"])
        except FileNotFoundError:
            return False
        return False

    def is_junction(self) -> bool:
        return False

    def is_block_device(self) -> bool:
        return False

    def is_char_device(self) -> bool:
        return False

    def is_fifo(self) -> bool:
        return False

    def is_socket(self) -> bool:
        return False

    def is_reserved(self) -> bool:
        return False

    def expanduser(self) -> Self:
        return self

    def glob(
        self,
        pattern: str,
        *,
        case_sensitive: bool = UNSET_DEFAULT,
        recurse_symlinks: bool = UNSET_DEFAULT,
    ) -> Iterator[Self]:
        if case_sensitive is not UNSET_DEFAULT:
            warnings.warn(
                "UPath.glob(): case_sensitive is currently ignored.",
                UserWarning,
                stacklevel=2,
            )
        if recurse_symlinks is not UNSET_DEFAULT:
            warnings.warn(
                "UPath.glob(): recurse_symlinks is currently ignored.",
                UserWarning,
                stacklevel=2,
            )
        if self._relative_base is not None:
            self = self.absolute()
        path_pattern = self.joinpath(pattern).path
        sep = self.parser.sep
        base = self.path
        for name in self.fs.glob(path_pattern):
            name = name.removeprefix(base).removeprefix(sep)
            yield self.joinpath(name)

    def rglob(
        self,
        pattern: str,
        *,
        case_sensitive: bool = UNSET_DEFAULT,
        recurse_symlinks: bool = UNSET_DEFAULT,
    ) -> Iterator[Self]:
        if case_sensitive is not UNSET_DEFAULT:
            warnings.warn(
                "UPath.glob(): case_sensitive is currently ignored.",
                UserWarning,
                stacklevel=2,
            )
        if recurse_symlinks is not UNSET_DEFAULT:
            warnings.warn(
                "UPath.glob(): recurse_symlinks is currently ignored.",
                UserWarning,
                stacklevel=2,
            )
        if _FSSPEC_HAS_WORKING_GLOB is None:
            _check_fsspec_has_working_glob()

        if _FSSPEC_HAS_WORKING_GLOB:
            r_path_pattern = self.joinpath("**", pattern).path
            sep = self.parser.sep
            base = self.path
            for name in self.fs.glob(r_path_pattern):
                name = name.removeprefix(base).removeprefix(sep)
                yield self.joinpath(name)

        else:
            path_pattern = self.joinpath(pattern).path
            r_path_pattern = self.joinpath("**", pattern).path
            sep = self.parser.sep
            base = self.path
            seen = set()
            for p in (path_pattern, r_path_pattern):
                for name in self.fs.glob(p):
                    name = name.removeprefix(base).removeprefix(sep)
                    if name in seen:
                        continue
                    else:
                        seen.add(name)
                        yield self.joinpath(name)

    def owner(self) -> str:
        _raise_unsupported(type(self).__name__, "owner")

    def group(self) -> str:
        _raise_unsupported(type(self).__name__, "group")

    def absolute(self) -> Self:
        if self._relative_base is not None:
            return self.cwd().joinpath(self.__vfspath__())
        return self

    def is_absolute(self) -> bool:
        if self._relative_base is not None:
            return False
        else:
            return self.parser.isabs(self.__vfspath__())

    def __eq__(self, other: object) -> bool:
        """UPaths are considered equal if their protocol, path and
        storage_options are equal."""
        if not isinstance(other, UPath):
            return NotImplemented

        # For relative paths, compare the string representation instead of path
        if (
            self._relative_base is not None
            or getattr(other, "_relative_base", None) is not None
        ):
            # If both are relative paths, compare just the relative strings
            if (
                self._relative_base is not None
                and getattr(other, "_relative_base", None) is not None
            ):
                return str(self) == str(other)
            else:
                # One is relative, one is not - they can't be equal
                return False

        return (
            self.__vfspath__() == other.__vfspath__()
            and self.protocol == other.protocol
            and self.storage_options == other.storage_options
        )

    def __hash__(self) -> int:
        """The returned hash is based on the protocol and path only.

        Note: in the future, if hash collisions become an issue, we
          can add `fsspec.utils.tokenize(storage_options)`
        """
        return hash((self.protocol, self.__vfspath__()))

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, UPath) or self.parser is not other.parser:
            return NotImplemented
        return self.__vfspath__() < other.__vfspath__()

    def __le__(self, other: object) -> bool:
        if not isinstance(other, UPath) or self.parser is not other.parser:
            return NotImplemented
        return self.__vfspath__() <= other.__vfspath__()

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, UPath) or self.parser is not other.parser:
            return NotImplemented
        return self.__vfspath__() > other.__vfspath__()

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, UPath) or self.parser is not other.parser:
            return NotImplemented
        return self.__vfspath__() >= other.__vfspath__()

    def resolve(self, strict: bool = False) -> Self:
        if self._relative_base is not None:
            self = self.absolute()
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

    def touch(self, mode: int = 0o666, exist_ok: bool = True) -> None:
        exists = self.fs.exists(self.path)
        if exists and not exist_ok:
            raise FileExistsError(str(self))
        if not exists:
            self.fs.touch(self.path, truncate=True)
        else:
            try:
                self.fs.touch(self.path, truncate=False)
            except (NotImplementedError, ValueError):
                pass  # unsupported by filesystem

    def lchmod(self, mode: int) -> None:
        _raise_unsupported(type(self).__name__, "lchmod")

    def unlink(self, missing_ok: bool = False) -> None:
        if not self.exists():
            if not missing_ok:
                raise FileNotFoundError(str(self))
            return
        self.fs.rm(self.path, recursive=False)

    def rmdir(self, recursive: bool = True) -> None:  # fixme: non-standard
        if not self.is_dir():
            raise NotADirectoryError(str(self))
        if not recursive and next(self.iterdir()):  # type: ignore[arg-type]
            raise OSError(f"Not recursive and directory not empty: {self}")
        self.fs.rm(self.path, recursive=recursive)

    def rename(
        self,
        target: WritablePathLike,
        *,  # note: non-standard compared to pathlib
        recursive: bool = UNSET_DEFAULT,
        maxdepth: int | None = UNSET_DEFAULT,
        **kwargs: Any,
    ) -> Self:
        target_protocol = get_upath_protocol(target)
        if target_protocol and target_protocol != self.protocol:
            raise ValueError(
                f"expected protocol {self.protocol!r}, got: {target_protocol!r}"
            )
        if not isinstance(target, UPath):
            target = str(target)
            if target_protocol or (self.anchor and target.startswith(self.anchor)):
                target = self.with_segments(target)
            else:
                target = UPath(target)
        if target == self:
            return self
        if self._relative_base is not None:
            self = self.absolute()
        target_protocol = get_upath_protocol(target)
        if target_protocol:
            target_ = target
            # avoid calling .resolve for subclasses of UPath
            if ".." in target_.parts or "." in target_.parts:
                target_ = target_.resolve()
        else:
            parent = self.parent
            # avoid calling .resolve for subclasses of UPath
            if ".." in parent.parts or "." in parent.parts:
                parent = parent.resolve()
            target_ = parent.joinpath(posixpath.normpath(target.path))
        if recursive is not UNSET_DEFAULT:
            kwargs["recursive"] = recursive
        if maxdepth is not UNSET_DEFAULT:
            kwargs["maxdepth"] = maxdepth
        self.fs.mv(
            self.path,
            target_.path,
            **kwargs,
        )
        return self.with_segments(target_)

    def replace(self, target: WritablePathLike) -> Self:
        _raise_unsupported(type(self).__name__, "replace")

    @property
    def drive(self) -> str:
        if self._relative_base is not None:
            return ""
        return self.parser.splitroot(str(self))[0]

    @property
    def root(self) -> str:
        if self._relative_base is not None:
            return ""
        return self.parser.splitroot(str(self))[1]

    def __reduce__(self):
        if self._relative_base is None:
            args = (self.__vfspath__(),)
            kwargs = {
                "protocol": self._protocol,
                **self._storage_options,
            }
        else:
            args = (self._relative_base, self.__vfspath__())
            # Include _relative_base in the state if it's set
            kwargs = {
                "protocol": self._protocol,
                **self._storage_options,
                "_relative_base": self._relative_base,
            }
        return _make_instance, (type(self), args, kwargs)

    @classmethod
    def from_uri(cls, uri: str, **storage_options: Any) -> Self:
        return cls(uri, **storage_options)

    def as_uri(self) -> str:
        if self._relative_base is not None:
            raise ValueError(
                f"relative path can't be expressed as a {self.protocol} URI"
            )
        return str(self)

    def as_posix(self) -> str:
        return str(self)

    def samefile(self, other_path) -> bool:
        st = self.stat()
        if isinstance(other_path, UPath):
            other_st = other_path.stat()
        else:
            other_st = self.with_segments(other_path).stat()
        return st == other_st

    @classmethod
    def cwd(cls) -> Self:
        if cls is UPath:
            # default behavior for UPath.cwd() is to return local cwd
            return get_upath_class("").cwd()  # type: ignore[union-attr,return-value]
        else:
            _raise_unsupported(cls.__name__, "cwd")

    @classmethod
    def home(cls) -> Self:
        if cls is UPath:
            return get_upath_class("").home()  # type: ignore[union-attr,return-value]
        else:
            _raise_unsupported(cls.__name__, "home")

    def relative_to(  # type: ignore[override]
        self,
        other: Self | str,
        /,
        *_deprecated,
        walk_up: bool = False,
    ) -> Self:
        if walk_up:
            raise NotImplementedError("walk_up=True is not implemented yet")

        if isinstance(other, UPath):
            # revisit: ...
            if self.__class__ is not other.__class__:
                raise ValueError(
                    "incompatible protocols:"
                    f" {self._protocol!r} != {other._protocol!r}"
                )
            if self.storage_options != other.storage_options:
                raise ValueError(
                    "incompatible storage_options:"
                    f" {self.storage_options!r} != {other.storage_options!r}"
                )
        elif isinstance(other, str):
            other = self.with_segments(other)
        else:
            raise TypeError(f"expected UPath or str, got {type(other).__name__}")

        if other not in self.parents and self != other:
            raise ValueError(f"{self!s} is not in the subpath of {other!s}")
        else:
            rel = copy(self)
            rel._relative_base = str(other)
            return rel

    def is_relative_to(self, other, /, *_deprecated) -> bool:  # type: ignore[override]
        if isinstance(other, UPath) and self.storage_options != other.storage_options:
            return False
        return self == other or other in self.parents

    def hardlink_to(self, target: ReadablePathLike) -> None:
        raise NotImplementedError

    def match(self, pattern: str) -> bool:
        # fixme: hacky emulation of match. needs tests...
        if not pattern:
            raise ValueError("pattern cannot be empty")
        return self.full_match(pattern.replace("**", "*"))

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: Any, _handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        from pydantic_core import core_schema

        str_schema = core_schema.chain_schema(
            [
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(
                    lambda path: {
                        "path": path,
                        "protocol": None,
                        "storage_options": {},
                    },
                ),
            ]
        )

        object_schema = core_schema.typed_dict_schema(
            {
                "path": core_schema.typed_dict_field(
                    core_schema.str_schema(), required=True
                ),
                "protocol": core_schema.typed_dict_field(
                    core_schema.with_default_schema(
                        core_schema.nullable_schema(
                            core_schema.str_schema(),
                        ),
                        default=None,
                    ),
                    required=False,
                ),
                "storage_options": core_schema.typed_dict_field(
                    core_schema.with_default_schema(
                        core_schema.dict_schema(
                            core_schema.str_schema(),
                            core_schema.any_schema(),
                        ),
                        default_factory=dict,
                    ),
                    required=False,
                ),
            },
            extra_behavior="forbid",
        )

        deserialization_schema = core_schema.chain_schema(
            [
                core_schema.union_schema([str_schema, object_schema]),
                core_schema.no_info_plain_validator_function(
                    lambda dct: cls(
                        dct.pop("path"),
                        protocol=dct.pop("protocol"),
                        **dct["storage_options"],
                    )
                ),
            ]
        )

        serialization_schema = core_schema.plain_serializer_function_ser_schema(
            lambda u: {
                "path": u.path,
                "protocol": u.protocol,
                "storage_options": dict(u.storage_options),
            }
        )

        return core_schema.json_or_python_schema(
            json_schema=deserialization_schema,
            python_schema=core_schema.union_schema(
                [core_schema.is_instance_schema(UPath), deserialization_schema]
            ),
            serialization=serialization_schema,
        )
