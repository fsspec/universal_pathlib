"""upath._parser

Provides a pathlib_abc.ParserBase implementation for fsspec filesystems.
"""

from __future__ import annotations

import os
import posixpath
import sys
import warnings
from functools import lru_cache
from typing import TYPE_CHECKING
from typing import Any
from typing import Literal
from typing import Protocol
from typing import TypedDict
from urllib.parse import SplitResult
from urllib.parse import urlsplit

from fsspec import AbstractFileSystem
from fsspec.registry import known_implementations
from fsspec.registry import registry as _class_registry
from pathlib_abc import ParserBase

from upath._compat import str_remove_suffix
from upath._flavour_sources import flavour_registry as _flavour_registry
from upath._uris import normalize_empty_netloc

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from upath.core import PureUPath
    from upath.core import UPathLike


__all__ = [
    "FSSpecParserDescriptor",
    "FSSpecParser",
]

# note: this changed in Python https://github.com/python/cpython/pull/113563
URLSPLIT_NORMALIZES_DOUBLE_SLASH = (
    SplitResult._make(("", "", "//", "", "")).geturl() == "////"
)


class ParserProtocol(Protocol):
    """parser interface of fsspec filesystems"""

    protocol: str | tuple[str, ...]
    root_marker: Literal["/", ""]
    sep: Literal["/"]

    @classmethod
    def _strip_protocol(cls, path: UPathLike) -> str: ...

    @staticmethod
    def _get_kwargs_from_urls(path: UPathLike) -> dict[str, Any]: ...

    @classmethod
    def _parent(cls, path: UPathLike) -> str: ...


class ProtocolConfig(TypedDict):
    netloc_is_anchor: set[str]
    supports_empty_parts: set[str]
    meaningful_trailing_slash: set[str]


# === registries of fsspec filesystems for uri parsing ==================

pure_parser_registry: dict[str, ParserProtocol] = _flavour_registry  # type: ignore[assignment]
concrete_fs_registry: dict[str, ParserProtocol] = _class_registry  # type: ignore[assignment]


# === parser implementations ===========================================


class FSSpecParserDescriptor:
    """Non-data descriptor for the `parser` attribute of a `UPath` subclass."""

    def __init__(self) -> None:
        self._owner: type[PureUPath] | None = None

    def __set_name__(self, owner: type[PureUPath], name: str) -> None:
        self._owner = owner

    def __get__(
        self, instance: PureUPath | None, owner: type[PureUPath] | None = None
    ) -> FSSpecParser:
        if instance is not None:
            return FSSpecParser.from_protocol(instance.protocol)
        elif owner is not None:
            if not owner._supported_protocols:
                raise AttributeError(
                    "Cannot access `parser` attribute on the generic UPath class."
                )
            else:
                return FSSpecParser.from_protocol(owner._supported_protocols[0])
        else:
            return self  # type: ignore

    def __repr__(self):
        return f"<{self.__class__.__name__} of {self._owner!r}>"


class FSSpecParser(ParserBase):
    """parser class for universal_pathlib

    **INTERNAL AND VERY MUCH EXPERIMENTAL**

    Implements the fsspec compatible low-level lexical operations on
    PurePathBase-like objects.

    Note:
        In case you find yourself in need of subclassing this class,
        please open an issue in the universal_pathlib issue tracker:
        https://github.com/fsspec/universal_pathlib/issues
        Ideally we can find a way to make your use-case work by adding
        more functionality to this class.

    """

    # Note:
    #   It would be ideal if there would be a way to avoid the need for
    #   indicating the following settings via the protocol. This is a
    #   workaround to be able to implement the parser correctly. Still
    #   have to wrap my head around how to do this in a better way.
    # TODO:
    #   These settings should be configured on the UPath class?!?
    protocol_config: ProtocolConfig = {
        "netloc_is_anchor": {
            "http",
            "https",
            "s3",
            "s3a",
            "sftp",
            "ssh",
            "smb",
            "gs",
            "gcs",
            "az",
            "adl",
            "abfs",
            "webdav+http",
            "webdav+https",
        },
        "supports_empty_parts": {
            "http",
            "https",
            "s3",
            "s3a",
            "gs",
            "gcs",
            "az",
            "adl",
            "abfs",
        },
        "meaningful_trailing_slash": {
            "http",
            "https",
        },
    }

    def __init__(
        self,
        spec: ParserProtocol,
        *,
        netloc_is_anchor: bool = False,
        supports_empty_parts: bool = False,
        meaningful_trailing_slash: bool = False,
    ) -> None:
        """initialize the parser with the given fsspec filesystem"""
        self._spec = spec

        # netloc is considered an anchor, influences:
        #   - splitdrive
        #   - join
        self.netloc_is_anchor = bool(netloc_is_anchor)

        # supports empty parts, influences:
        #   - join
        self.supports_empty_parts = bool(supports_empty_parts)

        # meaningful trailing slash, influences:
        #   - join
        self.has_meaningful_trailing_slash = bool(meaningful_trailing_slash)

    @classmethod
    @lru_cache(maxsize=None)
    def from_protocol(cls, protocol: str) -> Self:
        """return the fsspec flavour for the given protocol"""

        _c = cls.protocol_config
        config = {
            "netloc_is_anchor": protocol in _c["netloc_is_anchor"],
            "supports_empty_parts": protocol in _c["supports_empty_parts"],
            "meaningful_trailing_slash": protocol in _c["meaningful_trailing_slash"],
        }

        # first try to get an already imported fsspec filesystem class
        try:
            return cls(concrete_fs_registry[protocol], **config)
        except KeyError:
            pass
        # next try to get the flavour from the generated flavour registry
        # to avoid imports
        try:
            return cls(pure_parser_registry[protocol], **config)
        except KeyError:
            pass
        # finally fallback to a default flavour for the protocol
        if protocol in known_implementations:
            warnings.warn(
                f"Could not find default for known protocol {protocol!r}."
                " Creating a default flavour for it. Please report this"
                " to the universal_pathlib issue tracker.",
                UserWarning,
                stacklevel=2,
            )
        spec: Any = type(
            f"{protocol.title()}FileSystem",
            (AbstractFileSystem,),
            {"protocol": protocol},
        )
        return cls(spec, **config)

    def __repr__(self):
        if isinstance(self._spec, type):
            return f"<{type(self).__name__} wrapping class {self._spec.__name__}>"
        else:
            return f"<{type(self).__name__} wrapping instance {self._spec!r} of {self._spec.__class__.__name__}>"

    # === fsspec.AbstractFileSystem ===================================

    @property
    def protocol(self) -> tuple[str, ...]:
        if isinstance(self._spec.protocol, str):
            return (self._spec.protocol,)
        else:
            return self._spec.protocol

    @property
    def root_marker(self) -> str:
        return self._spec.root_marker

    @property
    def local_file(self) -> bool:
        return bool(getattr(self._spec, "local_file", False))

    @staticmethod
    def stringify_path(pth: UPathLike) -> str:
        if isinstance(pth, str):
            out = pth
        elif hasattr(pth, "__fspath__") and pth.__fspath__ is not None:
            out = pth.__fspath__()
        elif isinstance(pth, os.PathLike):
            out = str(pth)
        elif hasattr(pth, "path"):  # type: ignore[unreachable]
            out = pth.path
        else:
            out = str(pth)
        return normalize_empty_netloc(out)

    def strip_protocol(self, pth: UPathLike) -> str:
        pth = self.stringify_path(pth)
        return self._spec._strip_protocol(pth)

    def get_kwargs_from_url(self, url: UPathLike) -> dict[str, Any]:
        # NOTE: the public variant is _from_url not _from_urls
        if hasattr(url, "storage_options"):
            return dict(url.storage_options)
        url = self.stringify_path(url)
        return self._spec._get_kwargs_from_urls(url)

    def parent(self, path: UPathLike) -> str:
        path = self.stringify_path(path)
        return self._spec._parent(path)

    # === pathlib_abc.ParserBase =====================================

    @property
    def sep(self) -> str:
        return self._spec.sep

    def join(self, path: UPathLike, *paths: UPathLike) -> str:
        if self.netloc_is_anchor:
            drv, p0 = self.splitdrive(path)
            pN = list(map(self.stringify_path, paths))
            if not drv and not p0:
                path, *pN = pN
                drv, p0 = self.splitdrive(path)
            p0 = p0 or self.sep
        else:
            p0 = str(self.strip_protocol(path))
            pN = list(map(self.stringify_path, paths))
            drv = ""
        if self.supports_empty_parts:
            return drv + self.sep.join([str_remove_suffix(p0, self.sep), *pN])
        else:
            return drv + posixpath.join(p0, *pN)

    def split(self, path: UPathLike) -> tuple[str, str]:
        stripped_path = self.strip_protocol(path)
        head = self.parent(stripped_path) or self.root_marker
        if head:
            return head, stripped_path[len(head) + 1 :]
        else:
            return "", stripped_path

    def splitdrive(self, path: UPathLike) -> tuple[str, str]:
        path = self.strip_protocol(path)
        if self.netloc_is_anchor:
            u = urlsplit(path)
            if u.scheme:
                # cases like: "http://example.com/foo/bar"
                drive = u._replace(path="", query="", fragment="").geturl()
                rest = u._replace(scheme="", netloc="").geturl()
                if URLSPLIT_NORMALIZES_DOUBLE_SLASH and u.path.startswith("//"):
                    # see: fsspec/universal_pathlib#233
                    rest = rest[2:]
                return drive, rest or self.root_marker or self.sep
            else:
                # cases like: "bucket/some/special/key"
                drive, root, tail = path.partition(self.sep)
                return drive, root + tail
        elif self.local_file:
            return os.path.splitdrive(path)
        else:
            # all other cases don't have a drive
            return "", path

    def splitext(self, path: UPathLike) -> tuple[str, str]:
        path = self.stringify_path(path)
        head, sep, tail = path.rpartition(self.sep)
        name, dot, ext = tail.rpartition(".")
        if name:
            return head + sep + name, dot + ext
        else:
            return path, ""

    def normcase(self, path: UPathLike) -> str:
        if self.local_file:
            return os.path.normcase(self.stringify_path(path))
        else:
            return self.stringify_path(path)

    def isabs(self, path: UPathLike) -> bool:
        path = self.strip_protocol(path)
        if self.local_file:
            return os.path.isabs(path)
        else:
            return path.startswith(self.root_marker)
