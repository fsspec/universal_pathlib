"""upath.core module: UPath base class implementation"""

from __future__ import annotations

import sys
import warnings
from abc import ABCMeta
from abc import abstractmethod
from collections.abc import Iterator
from collections.abc import Mapping
from collections.abc import Sequence
from copy import copy
from pathlib import PurePath
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
from upath.types import StatResultType
from upath.types import SupportsPathLike
from upath.types import UPathParser
from upath.types import WritablePath
from upath.types import WritablePathLike

if sys.version_info >= (3, 13):
    from pathlib import UnsupportedOperation
else:
    UnsupportedOperation = NotImplementedError
    """Raised when an unsupported operation is called on a path object."""

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

__all__ = [
    "UPath",
    "UnsupportedOperation",
]

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
    raise UnsupportedOperation(f"{cls_name}.{method}() is unsupported")


class _IncompatibleProtocolError(TypeError, ValueError):
    """switch to TypeError for incompatible protocols in a backward compatible way.

    !!! Do not use this exception directly !!!
    """


class _UPathMeta(ABCMeta):
    """metaclass for UPath to customize instance creation

    There are two main reasons for this metaclass:
    - support copying UPath instances via UPath(existing_upath)
    - force calling __init__ on instance creation for instances of a non-subclass
    """

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
    """Mixin class for UPath to allow sharing some common functionality
    between UPath and PosixUPath/WindowsUPath.
    """

    __slots__ = ()

    @property
    @abstractmethod
    def parser(self) -> UPathParser:
        """The parser (flavour) for this UPath instance."""
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
        """The fsspec protocol for the path.

        Note
        ----
        Protocols are linked to upath and fsspec filesystems via the
        `upath.registry` and `fsspec.registry` modules. They basically
        represent the URI scheme used for the specific filesystem.

        Examples
        --------
        >>> from upath import UPath
        >>> p0 = UPath("s3://my-bucket/path/to/file.txt")
        >>> p0.protocol
        's3'
        >>> p1 = UPath("/foo/bar/baz.txt", protocol="memory")
        >>> p1.protocol
        'memory'

        """
        return self._protocol

    @property
    def storage_options(self) -> Mapping[str, Any]:
        """The read-only fsspec storage options for the path.

        Note
        ----
        Storage options are specific to each fsspec filesystem and
        can include parameters such as authentication credentials,
        connection settings, and other options that affect how the
        filesystem interacts with the underlying storage.

        Examples
        --------
        >>> from upath import UPath
        >>> p = UPath("s3://my-bucket/path/to/file.txt", anon=True)
        >>> p.storage_options['anon']
        True

        """
        return MappingProxyType(self._storage_options)

    @property
    def fs(self) -> AbstractFileSystem:
        """The cached fsspec filesystem instance for the path.

        This is the underlying fsspec filesystem instance. It's
        instantiated on first filesystem access and cached. Can
        be used to access fsspec-specific functionality not exposed
        by the UPath API.

        Examples
        --------
        >>> from upath import UPath
        >>> p = UPath("s3://my-bucket/path/to/file.txt")
        >>> p.fs
        <s3fs.core.S3FileSystem object at 0x...>
        >>> p.fs.get_tags(p.path)
        {'VersionId': 'null', 'ContentLength': 12345, ...}

        """
        try:
            return self._fs_cached
        except AttributeError:
            fs = self._fs_cached = self._fs_factory(
                str(self), self.protocol, self.storage_options
            )
            return fs

    @property
    def path(self) -> str:
        """The path used by fsspec filesystem.

        FSSpec filesystems usually handle paths stripped of protocol.
        This property returns the path suitable for use with the
        underlying fsspec filesystem. It guarantees that a filesystem's
        strip_protocol method is applied correctly.

        Examples
        --------
        >>> from upath import UPath
        >>> p = UPath("memory:///foo/bar.txt")
        >>> str(p)
        'memory:///foo/bar.txt'
        >>> p.path
        '/foo/bar.txt'
        >>> p.fs.exists(p.path)
        True

        """
        if self._relative_base is not None:
            try:
                # For relative paths, we need to resolve to absolute path
                current_dir = self.cwd()  # type: ignore[attr-defined]
            except NotImplementedError:
                raise UnsupportedOperation(
                    f"fsspec paths can not be relative and"
                    f" {type(self).__name__}.cwd() is unsupported"
                ) from None
            # Join the current directory with the relative path
            if (self_path := str(self)) == ".":
                path = str(current_dir)
            else:
                path = current_dir.parser.join(str(current_dir), self_path)
            return self.parser.strip_protocol(path)
        return self._chain.active_path

    def joinuri(self, uri: JoinablePathLike) -> UPath:
        """Join with urljoin behavior for UPath instances.

        Examples
        --------
        >>> from upath import UPath
        >>> p = UPath("https://example.com/dir/subdir/")
        >>> p.joinuri("file.txt")
        HTTPSPath('https://example.com/dir/subdir/file.txt')
        >>> p.joinuri("/anotherdir/otherfile.txt")
        HTTPSPath('https://example.com/anotherdir/otherfile.txt')
        >>> p.joinuri("memory:///foo/bar.txt"
        MemoryPath('memory:///foo/bar.txt')

        """
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
        try:
            pth_protocol = get_upath_protocol(
                args[0] if args else "",
                protocol=protocol,
                storage_options=storage_options,
            )
        except ValueError as e:
            if "incompatible with" in str(e):
                raise _IncompatibleProtocolError(str(e)) from e
            raise
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
        """Initialize a UPath instance

        When instantiating a `UPath`, the detected or provided protocol determines
        the `UPath` subclass that will be instantiated. The protocol is looked up
        via the `get_upath_protocol` function, which loads the registered `UPath`
        implementation from the registry. If no `UPath` implementation is found for
        the detected protocol, but a registered `fsspec` filesystem exists for the
        protocol, a default dynamically created `UPath` implementation will be used.

        Parameters
        ----------
        *args :
            The path (or uri) segments to construct the UPath from. The first
            argument is used to detect the protocol if no protocol is provided.
        protocol :
            The protocol to use for the path.
        chain_parser :
            A chain parser instance for chained urlpaths. _(experimental)_
        **storage_options :
            Additional storage options for the path.

        """

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
            flavour = WrappedFileSystemFlavour.from_protocol(protocol)
            joined = flavour.join(chain.active_path, *args[1:])
            stripped = flavour.strip_protocol(joined)
            chain = chain.replace(path=stripped)
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
    """Base class for pathlike paths backed by an fsspec filesystem.

    Note
    ----
    The following attributes and methods are specific to UPath instances and are not
    available on pathlib.Path instances.

    Attributes
    ----------
    protocol :
        The fsspec protocol for the path.
    storage_options :
        The fsspec storage options for the path.
    path :
        The path that a fsspec filesystem can use.
    fs :
        The cached fsspec filesystem instance for the path.

    Methods
    -------
    joinuri(*parts) :
        Join URI parts to this path.


    Info
    ----
    Below are pathlib attributes and methods available on UPath instances.

    Attributes
    ----------
    drive :
        The drive component of the path.
    root :
        The root component of the path.
    anchor :
        The concatenation of the drive and root.
    parent :
        The logical parent of the path.
    parents :
        An immutable sequence providing access to the logical ancestors of the path.
    name :
        The final path component, excluding the drive and root, if any.
    suffix :
        The file extension of the final component, if any.
    suffixes :
        A list of the path's file extensions.
    stem :
        The final path component, without its suffix.
    info :
        Filesystem information about the path.
    parser :
        The path parser instance for parsing path segments.

    Methods
    -------
    __truediv__(key) :
        Combine this path with the argument using the `/` operator.
    __rtruediv__(key) :
        Combine the argument with this path using the `/` operator.
    as_posix() :
        Return the string representation of the path with forward slashes.
    is_absolute() :
        Return True if the path is absolute.
    is_relative_to(other) :
        Return True if the path is relative to another path.
    is_reserved() :
        Return True if the path is reserved under Windows.
    joinpath(*pathsegments) :
        Combine this path with one or several arguments, and return a new path.
    full_match(pattern, *, case_sensitive=None) :
        Match this path against the provided glob-style pattern.
    match(pattern, *, case_sensitive=None) :
        Match this path against the provided glob-style pattern.
    relative_to(other, walk_up=False) :
        Return a version of this path relative to another path.
    with_name(name) :
        Return a new path with the name changed.
    with_stem(stem) :
        Return a new path with the stem changed.
    with_suffix(suffix) :
        Return a new path with the suffix changed.
    with_segments(*pathsegments) :
        Construct a new path object from any number of path-like objects.
    from_uri(uri) :
        Return a new path from the given URI.
    as_uri() :
        Return the path as a URI.
    home() :
        Return a new path pointing to the user's home directory.
    expanduser() :
        Return a new path with expanded `~` constructs.
    cwd() :
        Return a new path pointing to the current working directory.
    absolute() :
        Make the path absolute, without normalization or resolving symlinks.
    resolve(strict=False) :
        Make the path absolute, resolving any symlinks.
    readlink() :
        Return the path to which the symbolic link points.
    stat(*, follow_symlinks=True) :
        Return the result of the stat() system call on this path.
    lstat() :
        Like stat(), but if the path points to a symlink, return the symlink's
        information.
    exists(*, follow_symlinks=True) :
        Return True if the path exists.
    is_file(*, follow_symlinks=True) :
        Return True if the path is a regular file.
    is_dir(*, follow_symlinks=True) :
        Return True if the path is a directory.
    is_symlink() :
        Return True if the path is a symbolic link.
    is_junction() :
        Return True if the path is a junction.
    is_mount() :
        Return True if the path is a mount point.
    is_socket() :
        Return True if the path is a socket.
    is_fifo() :
        Return True if the path is a FIFO.
    is_block_device() :
        Return True if the path is a block device.
    is_char_device() :
        Return True if the path is a character device.
    samefile(other_path) :
        Return True if this path points to the same file as other_path.
    open(mode='r', buffering=-1, encoding=None, errors=None, newline=None) :
        Open the file pointed to by the path.
    read_text(encoding=None, errors=None, newline=None) :
        Open the file in text mode, read it, and close the file.
    read_bytes() :
        Open the file in bytes mode, read it, and close the file.
    write_text(data, encoding=None, errors=None, newline=None) :
        Open the file in text mode, write to it, and close the file.
    write_bytes(data) :
        Open the file in bytes mode, write to it, and close the file.
    iterdir() :
        Yield path objects of the directory contents.
    glob(pattern, *, case_sensitive=None) :
        Iterate over this subtree and yield all existing files matching the
        given pattern.
    rglob(pattern, *, case_sensitive=None) :
        Recursively yield all existing files matching the given pattern.
    walk(top_down=True, on_error=None, follow_symlinks=False) :
        Generate the file names in a directory tree by walking the tree.
    touch(mode=0o666, exist_ok=True) :
        Create this file with the given access mode, if it doesn't exist.
    mkdir(mode=0o777, parents=False, exist_ok=False) :
        Create a new directory at this given path.
    symlink_to(target, target_is_directory=False) :
        Make this path a symbolic link pointing to target.
    hardlink_to(target) :
        Make this path a hard link pointing to the same file as target.
    copy(target, *, follow_symlinks=True, preserve_metadata=False) :
        Copy the contents of this file to the target file.
    copy_into(target_dir, *, follow_symlinks=True, preserve_metadata=False) :
        Copy this file or directory into the target directory.
    rename(target) :
        Rename this path to the target path.
    replace(target) :
        Rename this path to the target path, overwriting if that path exists.
    move(target) :
        Move this file or directory tree to the target path.
    move_into(target_dir) :
        Move this file or directory into the target directory.
    unlink(missing_ok=False) :
        Remove this file or link.
    rmdir() :
        Remove this directory.
    owner(*, follow_symlinks=True) :
        Return the login name of the file owner.
    group(*, follow_symlinks=True) :
        Return the group name of the file gid.
    chmod(mode, *, follow_symlinks=True) :
        Change the permissions of the path.
    lchmod(mode) :
        Like chmod() but, if the path points to a symlink, modify the symlink's
        permissions.

    """

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
            protocol: Literal["hf"],
            **_: Any,
        ) -> _uimpl.cloud.HfPath: ...
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
            protocol: Literal["ftp"],
            **_: Any,
        ) -> _uimpl.ftp.FTPPath: ...
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
        """Construct a new path object from any number of path-like objects."""
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
        """Provides sequence-like access to the filesystem path components.

        Examples
        --------
        >>> from upath import UPath
        >>> p = UPath("s3://my-bucket/path/to/file.txt")
        >>> p.parts
        ('my-bucket/', 'path', 'to', 'file.txt')
        >>> p2 = UPath("/foo/bar/baz.txt", protocol="memory")
        >>> p2.parts
        ('/', 'foo', 'bar', 'baz.txt')

        """
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
        """The concatenation of the drive and root or an empty string."""
        if self._relative_base is not None:
            return ""
        return self.drive + self.root

    @property
    def parent(self) -> Self:
        """The logical parent of the path.

        Examples
        --------
        >>> from upath import UPath
        >>> p = UPath("s3://my-bucket/path/to/file.txt")
        >>> p.parent
        S3Path('s3://my-bucket/path/to')

        """
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
        """A sequence providing access to the logical ancestors of the path.

        Examples
        --------
        >>> from upath import UPath
        >>> p = UPath("memory:///foo/bar/baz.txt")
        >>> list(p.parents)
        [
          MemoryPath('memory:///foo/bar'),
          MemoryPath('memory:///foo'),
          MemoryPath('memory:///'),
        ]

        """
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
        """Combine this path with one or several arguments, and return a new path.

        For one argument, this is equivalent to using the `/` operator.

        Examples
        --------
        >>> from upath import UPath
        >>> p = UPath("s3://my-bucket/path/to")
        >>> p.joinpath("file.txt")
        S3Path('s3://my-bucket/path/to/file.txt')

        """
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
        """
        A PathInfo object that exposes the file type and other file attributes
        of this path.

        Returns
        -------
        : UPathInfo
            The UPathInfo object for this path.
        """
        return UPathInfo(self)

    def iterdir(self) -> Iterator[Self]:
        """Yield path objects of the directory contents.

        Examples
        --------
        >>> from upath import UPath
        >>> p = UPath("memory:///foo/")
        >>> p.joinpath("bar.txt").touch()
        >>> p.joinpath("baz.txt").touch()
        >>> for child in p.iterdir():
        ...     print(child)
        MemoryPath('memory:///foo/bar.txt')
        MemoryPath('memory:///foo/baz.txt')

        """
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
        """
        Recursively copy this file or directory tree to the given destination.
        """
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
        """
        Copy this file or directory tree into the given existing directory.
        """
        if not isinstance(target_dir, UPath):
            return super().copy_into(self.with_segments(target_dir), **kwargs)
        else:
            return super().copy_into(target_dir, **kwargs)

    @overload
    def move(self, target: _WT, **kwargs: Any) -> _WT: ...

    @overload
    def move(self, target: SupportsPathLike | str, **kwargs: Any) -> Self: ...

    def move(self, target: _WT | SupportsPathLike | str, **kwargs: Any) -> _WT | UPath:
        """
        Recursively move this file or directory tree to the given destination.
        """
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
        """
        Move this file or directory tree into the given existing directory.
        """
        name = self.name
        if not name:
            raise ValueError(f"{self!r} has an empty name")
        elif hasattr(target_dir, "with_segments"):
            target = target_dir.with_segments(target_dir, name)  # type: ignore
        else:
            target = self.with_segments(target_dir, name)
        return self.move(target)

    def _copy_from(
        self,
        source: ReadablePath,
        follow_symlinks: bool = True,
        **kwargs: Any,
    ) -> None:
        return super()._copy_from(source, follow_symlinks)

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
        """
        Create a new directory at this given path.
        """
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
    ) -> StatResultType:
        """
        Return the result of the stat() system call on this path, like
        os.stat() does.

        Info
        ----
        For fsspec filesystems follow_symlinks is currently ignored.

        Returns
        -------
        : UPathStatResult
            The upath stat result for this path, emulating `os.stat_result`.

        """
        if not follow_symlinks:
            warnings.warn(
                f"{type(self).__name__}.stat(follow_symlinks=False):"
                " is currently ignored.",
                UserWarning,
                stacklevel=2,
            )
        return UPathStatResult.from_info(self.fs.info(self.path))

    def lstat(self) -> StatResultType:
        return self.stat(follow_symlinks=False)

    def chmod(self, mode: int, *, follow_symlinks: bool = True) -> None:
        _raise_unsupported(type(self).__name__, "chmod")

    def exists(self, *, follow_symlinks: bool = True) -> bool:
        """
        Whether this path exists.

        Info
        ----
        For fsspec filesystems follow_symlinks is currently ignored.
        """
        if not follow_symlinks:
            warnings.warn(
                f"{type(self).__name__}.exists() follow_symlinks=False"
                " is currently ignored.",
                UserWarning,
                stacklevel=2,
            )
        return self.fs.exists(self.path)

    def is_dir(self, *, follow_symlinks: bool = True) -> bool:
        """
        Whether this path is a directory.
        """
        if not follow_symlinks:
            warnings.warn(
                f"{type(self).__name__}.is_dir() follow_symlinks=False"
                " is currently ignored.",
                UserWarning,
                stacklevel=2,
            )
        return self.fs.isdir(self.path)

    def is_file(self, *, follow_symlinks: bool = True) -> bool:
        """
        Whether this path is a regular file.
        """
        if not follow_symlinks:
            warnings.warn(
                f"{type(self).__name__}.is_file() follow_symlinks=False"
                " is currently ignored.",
                UserWarning,
                stacklevel=2,
            )
        return self.fs.isfile(self.path)

    def is_mount(self) -> bool:
        """
        Check if this path is a mount point

        Info
        ----
        For fsspec filesystems this is always False.
        """
        return False

    def is_symlink(self) -> bool:
        """
        Whether this path is a symbolic link.
        """
        try:
            info = self.fs.info(self.path)
            if "islink" in info:
                return bool(info["islink"])
        except FileNotFoundError:
            return False
        return False

    def is_junction(self) -> bool:
        """
        Whether this path is a junction.

        Info
        ----
        For fsspec filesystems this is always False.
        """
        return False

    def is_block_device(self) -> bool:
        """
        Whether this path is a block device.

        Info
        ----
        For fsspec filesystems this is always False.
        """
        return False

    def is_char_device(self) -> bool:
        """
        Whether this path is a character device.

        Info
        ----
        For fsspec filesystems this is always False.
        """
        return False

    def is_fifo(self) -> bool:
        """
        Whether this path is a FIFO (named pipe).

        Info
        ----
        For fsspec filesystems this is always False.
        """
        return False

    def is_socket(self) -> bool:
        """
        Whether this path is a socket.

        Info
        ----
        For fsspec filesystems this is always False.
        """
        return False

    def is_reserved(self) -> bool:
        """
        Whether this path is reserved under Windows.

        Info
        ----
        For fsspec filesystems this is always False.
        """
        return False

    def expanduser(self) -> Self:
        """Return a new path with expanded `~` constructs.

        Info
        ----
        For fsspec filesystems this is currently a no-op.
        """
        return self

    def glob(
        self,
        pattern: str,
        *,
        case_sensitive: bool | None = None,
        recurse_symlinks: bool = False,
    ) -> Iterator[Self]:
        """Iterate over this subtree and yield all existing files (of any
        kind, including directories) matching the given relative pattern."""
        if case_sensitive is not None:
            warnings.warn(
                "UPath.glob(): case_sensitive is currently ignored.",
                UserWarning,
                stacklevel=2,
            )
        if recurse_symlinks:
            warnings.warn(
                "UPath.glob(): recurse_symlinks=True is currently ignored.",
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
        case_sensitive: bool | None = None,
        recurse_symlinks: bool = False,
    ) -> Iterator[Self]:
        """Recursively yield all existing files (of any kind, including
        directories) matching the given relative pattern, anywhere in
        this subtree.
        """
        if case_sensitive is not None:
            warnings.warn(
                "UPath.glob(): case_sensitive is currently ignored.",
                UserWarning,
                stacklevel=2,
            )
        if recurse_symlinks:
            warnings.warn(
                "UPath.glob(): recurse_symlinks=True is currently ignored.",
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

    def owner(self, *, follow_symlinks: bool = True) -> str:
        _raise_unsupported(type(self).__name__, "owner")

    def group(self, *, follow_symlinks: bool = True) -> str:
        _raise_unsupported(type(self).__name__, "group")

    def absolute(self) -> Self:
        """Return an absolute version of this path
        No normalization or symlink resolution is performed.

        Use resolve() to resolve symlinks and remove '..' segments.
        """
        if self._relative_base is not None:
            return self.cwd().joinpath(self.__vfspath__())
        return self

    def is_absolute(self) -> bool:
        """True if the path is absolute (has both a root and, if applicable,
        a drive)."""
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
        """
        Make the path absolute, resolving all symlinks on the way and also
        normalizing it.
        """
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
        """Create this file with the given access mode, if it doesn't exist."""
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
        """
        Remove this file or link.
        If the path is a directory, use rmdir() instead.
        """
        if not self.exists():
            if not missing_ok:
                raise FileNotFoundError(str(self))
            return
        self.fs.rm(self.path, recursive=False)

    def rmdir(self, recursive: bool = True) -> None:  # fixme: non-standard
        """
        Remove this directory.

        Warning
        -------
        This method is non-standard compared to pathlib.Path.rmdir(),
        as it supports a `recursive` parameter to remove non-empty
        directories and defaults to recursive deletion.

        This behavior is likely to change in future releases once
        `.delete()` is introduced.

        """
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
        """
        Rename this file or directory to the given target.

        The target path may be absolute or relative. Relative paths are
        interpreted relative to the current working directory, *not* the
        directory of the Path object.

        Returns the new Path instance pointing to the target path.

        Info
        ----
        For filesystems that don't have a root character, i.e. for which
        relative paths can be ambiguous, you can explicitly indicate a
        relative path via prefixing with `./`

        Warning
        -------
        This method is non-standard compared to pathlib.Path.rename(),
        as it supports `recursive` and `maxdepth` parameters for
        directory moves. This will be revisited in future releases.

        It's better to use `.move()` or `.move_into()` to avoid
        running into future compatibility issues.

        """
        # check protocol compatibility
        target_protocol = get_upath_protocol(target)
        if target_protocol and target_protocol != self.protocol:
            raise ValueError(
                f"expected protocol {self.protocol!r}, got: {target_protocol!r}"
            )
        # ensure target is an absolute UPath
        if not isinstance(target, type(self)):
            if isinstance(target, (UPath, PurePath)):
                target_str = target.as_posix()
            else:
                target_str = str(target)
            if target_protocol:
                # target protocol provided indicates absolute path
                target = self.with_segments(target_str)
            elif self.anchor and target_str.startswith(self.anchor):
                # self.anchor can be used to indicate absolute path
                target = self.with_segments(target_str)
            elif not self.anchor and target_str.startswith("./"):
                # indicate relative via "./"
                target = (
                    self.cwd()
                    .joinpath(target_str.removeprefix("./"))
                    .relative_to(self.cwd())
                )
            else:
                # all other cases
                target = self.cwd().joinpath(target_str).relative_to(self.cwd())
        # return early if renaming to same path
        if target == self:
            return self
        # ensure source and target are absolute
        source_abs = self.absolute()
        target_abs = target.absolute()
        # avoid calling .resolve for if not needed
        if ".." in target_abs.parts or "." in target_abs.parts:
            target_abs = target_abs.resolve()
        if kwargs:
            warnings.warn(
                "Passing additional keyword arguments to "
                f"{type(self).__name__}.rename() is deprecated and will be"
                " removed in future univeral-pathlib versions.",
                DeprecationWarning,
                stacklevel=2,
            )
        if recursive is not UNSET_DEFAULT:
            warnings.warn(
                f"{type(self).__name__}.rename()'s `recursive` keyword argument is"
                " deprecated and will be removed in future universal-pathlib versions."
                f" Please use {type(self).__name__}.move() or .move_into() instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            kwargs["recursive"] = recursive
        if maxdepth is not UNSET_DEFAULT:
            warnings.warn(
                f"{type(self).__name__}.rename()'s `maxdepth` keyword argument is"
                " deprecated and will be removed in future universal-pathlib versions.",
                DeprecationWarning,
                stacklevel=2,
            )
            kwargs["maxdepth"] = maxdepth
        self.fs.mv(
            source_abs.path,
            target_abs.path,
            **kwargs,
        )
        return target

    def replace(self, target: WritablePathLike) -> Self:
        """
        Rename this path to the target path, overwriting if that path exists.

        The target path may be absolute or relative. Relative paths are
        interpreted relative to the current working directory, *not* the
        directory of the Path object.

        Returns the new Path instance pointing to the target path.

        Warning
        -------
        This method is currently not implemented.

        """
        _raise_unsupported(type(self).__name__, "replace")

    @property
    def drive(self) -> str:
        """The drive prefix (letter or UNC path), if any.

        Info
        ----
        On non-Windows systems, the drive is always an empty string.
        On cloud storage systems, the drive is the bucket name or equivalent.
        """
        if self._relative_base is not None:
            return ""
        return self.parser.splitroot(str(self))[0]

    @property
    def root(self) -> str:
        """The root of the path, if any."""
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
        """Return the string representation of the path as a URI."""
        if self._relative_base is not None:
            raise ValueError(
                f"relative path can't be expressed as a {self.protocol} URI"
            )
        return str(self)

    def as_posix(self) -> str:
        """Return the string representation of the path with POSIX-style separators."""
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
        """
        Return a new UPath object representing the current working directory.

        Info
        ----
        None of the fsspec filesystems support a global current working
        directory, so this method only works for the base UPath class,
        returning the local current working directory.

        """
        if cls is UPath:
            # default behavior for UPath.cwd() is to return local cwd
            return get_upath_class("").cwd()  # type: ignore[union-attr,return-value]
        else:
            _raise_unsupported(cls.__name__, "cwd")

    @classmethod
    def home(cls) -> Self:
        """
        Return a new UPath object representing the user's home directory.

        Info
        ----
        None of the fsspec filesystems support user home directories,
        so this method only works for the base UPath class, returning the
        local user's home directory.

        """
        if cls is UPath:
            return get_upath_class("").home()  # type: ignore[union-attr,return-value]
        else:
            _raise_unsupported(cls.__name__, "home")

    def relative_to(  # type: ignore[override]
        self,
        other: Self | str,
        /,
        *_deprecated: Any,
        walk_up: bool = False,
    ) -> Self:
        """Return the relative path to another path identified by the passed
        arguments.  If the operation is not possible (because this is not
        related to the other path), raise ValueError.

        The *walk_up* parameter controls whether `..` may be used to resolve
        the path.
        """
        if walk_up:
            raise NotImplementedError("walk_up=True is not implemented yet")

        if isinstance(other, UPath):
            # revisit: ...
            if self.__class__ is not other.__class__:
                raise ValueError(
                    "incompatible protocols:"
                    f" {self.protocol!r} != {other.protocol!r}"
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
            rel._relative_base = other.path
            return rel

    def is_relative_to(
        self,
        other: Self | str,
        /,
        *_deprecated: Any,
    ) -> bool:  # type: ignore[override]
        """Return True if the path is relative to another path identified."""
        if isinstance(other, UPath) and self.storage_options != other.storage_options:
            return False
        elif isinstance(other, str):
            other = self.with_segments(other)
        return self == other or other in self.parents

    def hardlink_to(self, target: ReadablePathLike) -> None:
        _raise_unsupported(type(self).__name__, "hardlink_to")

    def full_match(
        self,
        pattern: str | SupportsPathLike,
        *,
        case_sensitive: bool | None = None,
    ) -> bool:
        """Match this path against the provided glob-style pattern.
        Return True if matching is successful, False otherwise.
        """
        if case_sensitive is not None:
            warnings.warn(
                f"{type(self).__name__}.full_match(): case_sensitive"
                " is currently ignored.",
                UserWarning,
                stacklevel=2,
            )
        return super().full_match(str(pattern))

    def match(
        self,
        path_pattern: str | SupportsPathLike,
        *,
        case_sensitive: bool | None = None,
    ) -> bool:
        """Match this path against the provided non-recursive glob-style pattern.
        Return True if matching is successful, False otherwise.
        """
        path_pattern = str(path_pattern)
        if not path_pattern:
            raise ValueError("pattern cannot be empty")
        if case_sensitive is not None:
            warnings.warn(
                f"{type(self).__name__}.match(): case_sensitive is currently ignored.",
                UserWarning,
                stacklevel=2,
            )
        return self.full_match(path_pattern.replace("**", "*"))

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
