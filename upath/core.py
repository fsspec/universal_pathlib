"""UPath core module"""

from __future__ import annotations

import os
import sys
import warnings
from copy import copy
from types import MappingProxyType
from typing import IO
from typing import TYPE_CHECKING
from typing import Any
from typing import BinaryIO
from typing import Callable
from typing import Final
from typing import Generator
from typing import Literal
from typing import Mapping
from typing import NoReturn
from typing import TextIO
from typing import overload
from urllib.parse import urlsplit

if sys.version_info >= (3, 11):
    from typing import Self
    from typing import TypeAlias
else:
    from typing_extensions import Self
    from typing_extensions import TypeAlias

from fsspec.registry import get_filesystem_class
from fsspec.spec import AbstractFileSystem

from upath._abc import PathBase
from upath._abc import PurePathBase
from upath._abc import UnsupportedOperation
from upath._compat import make_instance
from upath._parser import FSSpecParser
from upath._parser import FSSpecParserDescriptor
from upath._stat import UPathStatResult
from upath._uris import compatible_protocol
from upath._uris import get_upath_protocol
from upath._uris import upath_urijoin
from upath.registry import get_upath_class

if TYPE_CHECKING:
    from urllib.parse import SplitResult

__all__ = [
    "PureUPath",
    "UPath",
    "UPathLike",
]


def __getattr__(name: str) -> NoReturn:
    if name in {"_UriFlavour", "_FSSpecAccessor", "PT"}:
        raise AttributeError(f"{name!r} was removed in universal_pathlib>=0.3.0")
    else:
        raise AttributeError(name)


_UNSET: Final[Any] = object()


# the os.PathLike[str] equivalent for UPath-like objects
UPathLike: TypeAlias = "str | os.PathLike[str] | PureUPath"


class PureUPath(PurePathBase):
    """a pure version of UPath without the filesystem access

    Contrary to pathlib.PurePath, PureUPath is not a PathLike[AnyStr] subclass.
    It does not ship with a __fspath__ method, and it does not support the
    os.PathLike protocol. It also does not have a __bytes__ method. This means
    that PureUPath subclasses do not represent local files unless they
    explicitly implement the os.PathLike protocol.

    """

    __slots__ = (
        "_protocol",
        "_storage_options",
    )

    _protocol: str
    _storage_options: dict[str, Any]
    parser: FSSpecParser = FSSpecParserDescriptor()  # type: ignore[assignment]
    _supported_protocols: tuple[str, ...] = ()

    # === constructors ================================================

    def __init__(
        self,
        path: UPathLike,
        *paths: UPathLike,
        protocol: str | None = None,
        **storage_options: Any,
    ) -> None:
        # determine the protocol
        parsed_protocol = get_upath_protocol(
            path,
            protocol=protocol,
            storage_options=storage_options,
        )
        # todo:
        #   support checking if there is a UPath subclass for the protocol
        #   and use its _transform_init_args method to parse the args
        base_options = getattr(self, "_storage_options", {})
        _paths, protocol, storage_options = self._transform_init_args(
            (path, *paths),
            protocol or parsed_protocol,
            {**base_options, **storage_options},
        )
        if self._protocol != protocol and protocol:
            self._protocol = protocol
        else:
            self._protocol = parsed_protocol

        # check that UPath subclasses in args are compatible
        # TODO:
        #   Future versions of UPath could verify that storage_options
        #   can be combined between UPath instances. Not sure if this
        #   is really necessary though. A warning might be enough...
        if not compatible_protocol(self._protocol, *_paths):
            raise ValueError("can't combine incompatible UPath protocols")

        # set up the base class attributes
        super().__init__(*map(str, _paths))

        # retrieve storage_options
        # todo:
        #   support checking if there is a UPath subclass for the protocol
        #   and use its _parse_storage_options method to parse the storage_options
        self._storage_options = self._parse_storage_options(
            str(self), self._protocol, storage_options
        )

    @classmethod
    def _transform_init_args(
        cls,
        args: tuple[UPathLike, ...],
        protocol: str,
        storage_options: dict[str, Any],
    ) -> tuple[tuple[UPathLike, ...], str, dict[str, Any]]:
        """allow customization of init args in subclasses"""
        return args, protocol, storage_options

    @classmethod
    def _parse_storage_options(
        cls, urlpath: str, protocol: str, storage_options: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Parse storage_options from the urlpath"""
        pth_storage_options = FSSpecParser.from_protocol(protocol).get_kwargs_from_url(
            urlpath
        )
        return {**pth_storage_options, **storage_options}

    # === PureUPath custom API ========================================

    @property
    def protocol(self) -> str:
        """The fsspec protocol for the path."""
        return self._protocol

    @property
    def storage_options(self) -> Mapping[str, Any]:
        """The fsspec storage options for the path."""
        return MappingProxyType(self._storage_options)

    @property
    def path(self) -> str:
        """The path that a fsspec filesystem can use."""
        return self.parser.strip_protocol(super().__str__())

    def joinuri(self, uri: UPathLike) -> PureUPath:
        """Join with urljoin behavior for UPath instances"""
        # short circuit if the new uri uses a different protocol
        other_protocol = get_upath_protocol(uri)
        if other_protocol and other_protocol != self._protocol:
            return PureUPath(uri)
        else:
            return PureUPath(
                upath_urijoin(str(self), str(uri)),
                protocol=other_protocol or self._protocol,
                **self.storage_options,
            )

    @property
    def _url(self) -> SplitResult:
        # TODO:
        #   _url should be deprecated, but for now there is no good way of
        #   accessing query parameters from urlpaths...
        return urlsplit(self.as_posix())

    # === extra methods for pathlib.PurePath like interface ===========

    def __reduce__(self) -> tuple[
        Callable[..., Self],
        tuple[type, tuple[str, ...], dict],
    ]:
        """support pickling UPath instances"""
        args = (self._raw_path,)
        kwargs = {
            "protocol": self._protocol,
            **self._storage_options,
        }
        return make_instance, (type(self), args, kwargs)

    def __hash__(self) -> int:
        """The returned hash is based on the protocol and path only.

        Note: in the future, if hash collisions become an issue, we
          can add `fsspec.utils.tokenize(storage_options)`
        """
        return hash((self.protocol, self.path))

    def __eq__(self, other: object) -> bool:
        """PureUPaths are considered equal if their protocol, path and
        storage_options are equal."""
        if not isinstance(other, PureUPath):
            return NotImplemented
        return (
            self.path == other.path
            and self.protocol == other.protocol
            and self.storage_options == other.storage_options
        )

    def __lt__(self, other: object) -> bool:
        raise NotImplementedError("todo")  # fixme

    def __le__(self, other: object) -> bool:
        raise NotImplementedError("todo")  # fixme

    def __gt__(self, other: object) -> bool:
        raise NotImplementedError("todo")  # fixme

    def __ge__(self, other: object) -> bool:
        raise NotImplementedError("todo")  # fixme

    def __repr__(self):
        return f"{type(self).__name__}({str(self)!r}, protocol={self._protocol!r})"

    # === customized PurePathBase methods =============================

    def with_segments(self, *pathsegments: UPathLike) -> Self:
        return type(self)(
            *pathsegments,
            protocol=self._protocol,
            **self._storage_options,
        )

    def __str__(self) -> str:
        if self._protocol:
            return f"{self._protocol}://{self.path}"
        else:
            return self.path


class UPath(PathBase, PureUPath):
    """a concrete version of UPath with filesystem access"""

    __slots__ = ("_fs_cached",)

    _fs_cached: AbstractFileSystem
    _protocol_dispatch: bool | None = None

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
        super().__init__(*args, protocol=protocol, **storage_options)

    # === upath.UPath PUBLIC ADDITIONAL API ===========================

    def joinuri(self, uri: UPathLike) -> UPath:
        """Join with urljoin behavior for UPath instances"""
        # short circuit if the new uri uses a different protocol
        other_protocol = get_upath_protocol(uri)
        if other_protocol and other_protocol != self._protocol:
            return UPath(uri)
        else:
            return UPath(
                upath_urijoin(str(self), str(uri)),
                protocol=other_protocol or self._protocol,
                **self.storage_options,
            )

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

    # === upath.UPath CUSTOMIZABLE API ================================

    @classmethod
    def _fs_factory(
        cls, urlpath: str, protocol: str, storage_options: Mapping[str, Any]
    ) -> AbstractFileSystem:
        """Instantiate the filesystem_spec filesystem class"""
        fs_cls = get_filesystem_class(protocol)
        so_dct = fs_cls._get_kwargs_from_urls(urlpath)
        so_dct.update(storage_options)
        return fs_cls(**storage_options)

    # === upath.UPath changes =========================================

    def stat(
        self,
        *,
        follow_symlinks: bool = True,
    ) -> UPathStatResult:
        if not follow_symlinks:
            warnings.warn(
                "UPath.stat(follow_symlinks=False): follow_symlinks=False is"
                " currently ignored.",
                UserWarning,
                stacklevel=2,
            )
        return UPathStatResult.from_info(self.fs.stat(self.path))

    def lstat(self) -> UPathStatResult:
        return self.stat(follow_symlinks=False)

    def exists(self, *, follow_symlinks: bool = True) -> bool:
        if not follow_symlinks:
            warnings.warn(
                "UPath.stat(follow_symlinks=False): follow_symlinks=False is"
                " currently ignored.",
                UserWarning,
                stacklevel=2,
            )
        return self.fs.exists(self.path)

    def is_dir(self, *, follow_symlinks: bool = True) -> bool:
        if not follow_symlinks:
            warnings.warn(
                "UPath.stat(follow_symlinks=False): follow_symlinks=False is"
                " currently ignored.",
                UserWarning,
                stacklevel=2,
            )
        return self.fs.isdir(self.path)

    def is_file(self, *, follow_symlinks: bool = True) -> bool:
        if not follow_symlinks:
            warnings.warn(
                "UPath.stat(follow_symlinks=False): follow_symlinks=False is"
                " currently ignored.",
                UserWarning,
                stacklevel=2,
            )
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

    def samefile(self, other_path: UPathLike) -> bool:
        st = self.stat()
        if isinstance(other_path, UPath):
            other_st = other_path.stat()
        else:
            other_st = self.with_segments(other_path).stat()
        return st == other_st

    @overload
    def open(
        self,
        mode: Literal["rb", "ab", "wb"],
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> BinaryIO: ...

    @overload
    def open(
        self,
        mode: Literal["r", "a", "w", "rt", "at", "wt"] = "r",
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> TextIO: ...

    @overload
    def open(
        self,
        mode: str = "r",
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
        **fsspec_kwargs: Any,
    ) -> IO[Any]: ...

    def open(
        self,
        mode: str = "r",
        buffering: int = _UNSET,
        encoding: str | None = _UNSET,
        errors: str | None = _UNSET,
        newline: str | None = _UNSET,
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
        # translate pathlib buffering to fs block_size
        if buffering is not _UNSET:
            fsspec_kwargs.setdefault("block_size", buffering)
        for name, arg in zip(
            ("encoding", "errors", "newline"), (encoding, errors, newline)
        ):
            if arg is not _UNSET:
                warnings.warn(
                    f"UPath.open({name}=...) is currently ignored.",
                    UserWarning,
                    stacklevel=2,
                )
        return self.fs.open(self.path, mode=mode, **fsspec_kwargs)

    def iterdir(self) -> Generator[Self, None, None]:
        for name in self.fs.listdir(self.path):
            # fsspec returns dictionaries
            if isinstance(name, dict):
                name = name.get("name")
            if name in {".", ".."}:
                # Yielding a path object for these makes little sense
                continue
            # only want the path name with iterdir
            yield self.with_segments(name)

    def absolute(self) -> Self:
        return self

    @classmethod
    def cwd(cls) -> UPath:
        raise UnsupportedOperation(cls._unsupported_msg("cwd"))

    @classmethod
    def home(cls) -> UPath:
        raise UnsupportedOperation(cls._unsupported_msg("home"))

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

    def touch(
        self,
        mode: int = 0o666,
        exist_ok: bool = True,
    ) -> None:
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

    def rename(
        self,
        target: UPathLike,
        *,  # note: non-standard compared to pathlib
        recursive: bool = _UNSET,
        maxdepth: int | None = _UNSET,
        **kwargs: Any,
    ) -> Self:
        if self.with_segments(target).exists():
            raise FileExistsError(str(target))
        return self.replace(target, recursive=recursive, maxdepth=maxdepth, **kwargs)

    def replace(
        self,
        target: UPathLike,
        *,  # note: non-standard compared to pathlib
        recursive: bool = _UNSET,
        maxdepth: int | None = _UNSET,
        **kwargs: Any,
    ) -> Self:
        if isinstance(target, str) and self.storage_options:
            target = UPath(target, **self.storage_options)
        target_protocol = get_upath_protocol(target)
        if target_protocol:
            if target_protocol != self.protocol:
                raise ValueError(
                    f"expected protocol {self.protocol!r}, got: {target_protocol!r}"
                )
            if not isinstance(target, UPath):
                target_ = UPath(target, **self.storage_options)
            else:
                target_ = target
            # avoid calling .resolve for subclasses of UPath
            if ".." in target_.parts or "." in target_.parts:
                target_ = target_.resolve()
        else:
            parent = self.parent
            # avoid calling .resolve for subclasses of UPath
            if ".." in parent.parts or "." in parent.parts:
                parent = parent.resolve()
            target_ = parent.joinpath(os.path.normpath(str(target)))
        assert isinstance(target_, type(self)), "identical protocols enforced above"
        if recursive is not _UNSET:
            kwargs["recursive"] = recursive
        if maxdepth is not _UNSET:
            kwargs["maxdepth"] = maxdepth
        self.fs.mv(
            self.path,
            target_.path,
            **kwargs,
        )
        return target_

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

    def as_uri(self) -> str:
        return str(self)

    def is_reserved(self) -> bool:
        return False

    # === compatibility methods =======================================

    if sys.version_info < (3, 12):

        def link_to(self, target: str | Self) -> NoReturn:
            raise UnsupportedOperation(self._unsupported_msg("link_to"))
