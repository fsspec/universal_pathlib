from __future__ import annotations

import os
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
from typing import TextIO
from typing import overload
from urllib.parse import SplitResult
from urllib.parse import urlsplit

from fsspec.registry import get_filesystem_class
from fsspec.spec import AbstractFileSystem

from upath._chain import DEFAULT_CHAIN_PARSER
from upath._chain import Chain
from upath._chain import FSSpecChainParser
from upath._flavour import LazyFlavourDescriptor
from upath._flavour import upath_get_kwargs_from_url
from upath._flavour import upath_urijoin
from upath._protocol import compatible_protocol
from upath._protocol import get_upath_protocol
from upath._stat import UPathStatResult
from upath.registry import get_upath_class
from upath.types import UNSET_DEFAULT
from upath.types import JoinablePathLike
from upath.types import OpenablePath
from upath.types import PathInfo
from upath.types import ReadablePathLike
from upath.types import UPathParser
from upath.types import WritablePathLike

if TYPE_CHECKING:
    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self

    from pydantic import GetCoreSchemaHandler
    from pydantic_core.core_schema import CoreSchema


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
    return cls(*args, **kwargs)


def _explode_path(path, parser):
    split = parser.split
    path = parser.strip_protocol(path)
    parent, name = parser.split(path)
    names = []
    while path != parent:
        names.append(name)
        path = parent
        parent, name = split(path)
    return path, names


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


if sys.version_info >= (3, 11):
    _UPathMeta = ABCMeta

else:

    class _UPathMeta(ABCMeta):
        # pathlib 3.9 and 3.10 supported `Path[str]` but
        # did not return a GenericAlias but the class itself?
        def __getitem__(cls, key):
            return cls


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
        return self.parser.strip_protocol(self.__str__())

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
        assert issubclass(cls, UPath), "_UPathMixin should never be instantiated"

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

        # unparse fsspec chains
        if (
            not isinstance(part0, str)
            and hasattr(part0, "__fspath__")
            and part0.__fspath__ is not None
        ):
            _p0 = part0.__fspath__()
        else:
            _p0 = str(part0)
        segments = chain_parser.unchain(
            _p0, {"protocol": pth_protocol, **storage_options}
        )
        chain = Chain.from_list(segments)
        if not (cp := chain.current.protocol) == pth_protocol:
            warnings.warn(
                f"Unexpected protocol mismatch {cp!r} != {pth_protocol!r}",
                stacklevel=2,
            )
            chain = chain.replace(chain.current._replace(protocol=pth_protocol))

        # create a new instance
        if cls is UPath:
            # we called UPath() directly, and want an instance based on the
            # provided or detected protocol (i.e. upath_cls)
            obj: UPath = object.__new__(upath_cls)
            obj._chain = chain

            if cls not in upath_cls.mro():
                # we are not in the upath_cls mro, so we need to
                # call __init__ of the upath_cls
                upath_cls.__init__(obj, *args, protocol=pth_protocol, **storage_options)

        elif issubclass(cls, upath_cls):
            # we called a sub- or sub-sub-class of UPath, i.e. S3Path() and the
            # corresponding upath_cls based on protocol is equal-to or a
            # parent-of the cls.
            obj = object.__new__(cls)
            obj._chain = chain

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
            obj._chain = chain

            upath_cls.__init__(
                obj, *args, protocol=pth_protocol, **storage_options
            )  # type: ignore

        else:
            raise RuntimeError("UPath.__new__ expected cls to be subclass of UPath")

        obj._chain_parser = chain_parser
        return obj

    def __init__(
        self,
        *args: JoinablePathLike,
        protocol: str | None = None,
        chain_parser: FSSpecChainParser = DEFAULT_CHAIN_PARSER,
        **storage_options: Any,
    ) -> None:
        # allow subclasses to customize __init__ arg parsing
        try:
            base_options = self._chain.current.storage_options
        except AttributeError:
            base_options = {}
        args, protocol, storage_options = type(self)._transform_init_args(
            args, protocol or self._protocol, {**base_options, **storage_options}
        )
        if self._protocol != protocol and protocol:
            self._protocol = protocol

        # retrieve storage_options
        if args:
            args0 = args[0]
            if isinstance(args0, UPath):
                base_chain = args0._chain

            else:
                base_chain = self._chain

                if hasattr(args0, "__fspath__"):
                    _args0 = args0.__fspath__()
                else:
                    _args0 = str(args0)
                storage_options = type(self)._parse_storage_options(
                    _args0, protocol, storage_options
                )

            self._chain = base_chain.replace(
                storage_options={
                    **base_chain.current.storage_options,
                    **storage_options,
                }
            )

        elif storage_options:
            self._chain = self._chain.replace(
                storage_options={
                    **self._chain.current.storage_options,
                    **storage_options,
                }
            )

        # check that UPath subclasses in args are compatible
        # TODO:
        #   Future versions of UPath could verify that storage_options
        #   can be combined between UPath instances. Not sure if this
        #   is really necessary though. A warning might be enough...
        if not compatible_protocol(self._protocol, *args):
            raise ValueError("can't combine incompatible UPath protocols")

        if hasattr(self, "_raw_urlpaths"):
            return
        self._raw_urlpaths = args

    # --- deprecated attributes ---------------------------------------

    @property
    def _url(self) -> SplitResult:
        # TODO:
        #   _url should be deprecated, but for now there is no good way of
        #   accessing query parameters from urlpaths...
        return urlsplit(self.__str__())


class UPath(_UPathMixin, OpenablePath):
    __slots__ = (
        "_chain",
        "_chain_parser",
        "_fs_cached",
        "_raw_urlpaths",
    )

    if TYPE_CHECKING:
        _chain: Chain
        _chain_parser: FSSpecChainParser
        _fs_cached: bool
        _raw_urlpaths: Sequence[JoinablePathLike]

    # === JoinablePath attributes =====================================

    parser: UPathParser = LazyFlavourDescriptor()  # type: ignore[assignment]

    def with_segments(self, *pathsegments: JoinablePathLike) -> Self:
        return type(self)(
            *pathsegments,
            protocol=self._protocol,
            **self._storage_options,
        )

    def __str__(self) -> str:
        return self._chain_parser.chain(self._chain.to_list())[0]

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.path!r}, protocol={self._protocol!r})"

    # === JoinablePath overrides ======================================

    @property
    def parts(self) -> Sequence[str]:
        anchor, parts = _explode_path(self._chain.active_path, self.parser)
        if anchor:
            parts.append(anchor)
        return tuple(reversed(parts))

    def with_name(self, name) -> Self:
        """Return a new path with the file name changed."""
        split = self.parser.split
        if self.parser.sep in name:  # `split(name)[0]`
            raise ValueError(f"Invalid name {name!r}")
        path = str(self)
        path = path.removesuffix(split(path)[1]) + name
        return self.with_segments(path)

    # === ReadablePath attributes =====================================

    @property
    def info(self) -> PathInfo:
        raise NotImplementedError("todo")

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
            yield base.with_segments(str(base), name)

    def __open_rb__(self, buffering: int = -1) -> BinaryIO:
        block_size = _buffering2blocksize("wb", buffering)
        kw = {}
        if block_size is not None:
            kw["block_size"] = block_size
        return self.fs.open(self.path, mode="rb", **kw)

    def readlink(self) -> Self:
        raise NotImplementedError

    # --- WritablePath attributes -------------------------------------

    def symlink_to(
        self,
        target: ReadablePathLike,
        target_is_directory: bool = False,
    ) -> None:
        raise NotImplementedError

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

    def __open_wb__(self, buffering: int = -1) -> BinaryIO:
        block_size = _buffering2blocksize("wb", buffering)
        kw = {}
        if block_size is not None:
            kw["block_size"] = block_size
        return self.fs.open(self.path, mode="wb", **kw)

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
        follow_symlinks=True,
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
        raise NotImplementedError

    def exists(self, *, follow_symlinks=True) -> bool:
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
    ) -> Iterator[UPath]:
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
        path_pattern = self.joinpath(pattern).path
        sep = self.parser.sep
        base = self.fs._strip_protocol(self.path)
        for name in self.fs.glob(path_pattern):
            name = name.removeprefix(base).removeprefix(sep)
            yield self.joinpath(name)

    def rglob(
        self,
        pattern: str,
        *,
        case_sensitive: bool = UNSET_DEFAULT,
        recurse_symlinks: bool = UNSET_DEFAULT,
    ) -> Iterator[UPath]:
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
            base = self.fs._strip_protocol(self.path)
            for name in self.fs.glob(r_path_pattern):
                name = name.removeprefix(base).removeprefix(sep)
                yield self.joinpath(name)

        else:
            path_pattern = self.joinpath(pattern).path
            r_path_pattern = self.joinpath("**", pattern).path
            sep = self.parser.sep
            base = self.fs._strip_protocol(self.path)
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
        raise NotImplementedError

    def group(self) -> str:
        raise NotImplementedError

    def absolute(self) -> Self:
        return self

    def is_absolute(self) -> bool:
        return self.parser.isabs(str(self))

    def __eq__(self, other: object) -> bool:
        """UPaths are considered equal if their protocol, path and
        storage_options are equal."""
        if not isinstance(other, UPath):
            return NotImplemented
        return (
            self.path == other.path
            and self.protocol == other.protocol
            and self.storage_options == other.storage_options
        )

    def __hash__(self) -> int:
        """The returned hash is based on the protocol and path only.

        Note: in the future, if hash collisions become an issue, we
          can add `fsspec.utils.tokenize(storage_options)`
        """
        return hash((self.protocol, self.path))

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, UPath) or self.parser is not other.parser:
            return NotImplemented
        return self.path < other.path

    def __le__(self, other: object) -> bool:
        if not isinstance(other, UPath) or self.parser is not other.parser:
            return NotImplemented
        return self.path <= other.path

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, UPath) or self.parser is not other.parser:
            return NotImplemented
        return self.path > other.path

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, UPath) or self.parser is not other.parser:
            return NotImplemented
        return self.path >= other.path

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

    def touch(self, mode=0o666, exist_ok=True) -> None:
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
        raise NotImplementedError

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
        if isinstance(target, str) and self.storage_options:
            target = UPath(target, **self.storage_options)
        if target == self:
            return self
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
        raise NotImplementedError  # todo

    @property
    def drive(self) -> str:
        return self.parser.splitdrive(str(self))[0]

    @property
    def root(self) -> str:
        return self.parser.splitroot(str(self))[1]

    def __reduce__(self):
        args = tuple(self._raw_urlpaths)
        kwargs = {
            "protocol": self._protocol,
            **self._storage_options,
        }
        return _make_instance, (type(self), args, kwargs)

    def as_uri(self) -> str:
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
    def cwd(cls) -> UPath:
        if cls is UPath:
            return get_upath_class("").cwd()  # type: ignore[union-attr]
        else:
            raise NotImplementedError

    @classmethod
    def home(cls) -> UPath:
        if cls is UPath:
            return get_upath_class("").home()  # type: ignore[union-attr]
        else:
            raise NotImplementedError

    def relative_to(  # type: ignore[override]
        self,
        other,
        /,
        *_deprecated,
        walk_up=False,
    ) -> Self:
        if isinstance(other, UPath) and (
            (self.__class__ is not other.__class__)
            or (self.storage_options != other.storage_options)
        ):
            raise ValueError(
                "paths have different storage_options:"
                f" {self.storage_options!r} != {other.storage_options!r}"
            )
        return self  # super().relative_to(other, *_deprecated, walk_up=walk_up)

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

        deserialization_schema = core_schema.chain_schema(
            [
                core_schema.no_info_plain_validator_function(
                    lambda v: {"path": v} if isinstance(v, str) else v,
                ),
                core_schema.typed_dict_schema(
                    {
                        "path": core_schema.typed_dict_field(
                            core_schema.str_schema(), required=True
                        ),
                        "protocol": core_schema.typed_dict_field(
                            core_schema.with_default_schema(
                                core_schema.str_schema(), default=""
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
                ),
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
