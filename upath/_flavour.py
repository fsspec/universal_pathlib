from __future__ import annotations

import os.path
import posixpath
import sys
import warnings
from collections.abc import Mapping
from functools import lru_cache
from typing import TYPE_CHECKING
from typing import Any
from typing import TypedDict
from urllib.parse import SplitResult
from urllib.parse import urlsplit

from fsspec.registry import known_implementations
from fsspec.registry import registry as _class_registry
from fsspec.spec import AbstractFileSystem

import upath
from upath._flavour_sources import FileSystemFlavourBase
from upath._flavour_sources import flavour_registry
from upath._protocol import get_upath_protocol
from upath._protocol import normalize_empty_netloc
from upath.types import JoinablePathLike
from upath.types import UPathParser

if TYPE_CHECKING:
    if sys.version_info >= (3, 12):
        from typing import TypeAlias
    else:
        TypeAlias = Any

    from upath.core import UPath

__all__ = [
    "LazyFlavourDescriptor",
    "default_flavour",
    "upath_urijoin",
    "upath_get_kwargs_from_url",
    "upath_strip_protocol",
]

class_registry: Mapping[str, type[AbstractFileSystem]] = _class_registry


class AnyProtocolFileSystemFlavour(FileSystemFlavourBase):
    sep = "/"
    protocol = ()
    root_marker = "/"

    @classmethod
    def _strip_protocol(cls, path: str) -> str:
        protocol = get_upath_protocol(path)
        if path.startswith(protocol + "://"):
            path = path[len(protocol) + 3 :]
        elif path.startswith(protocol + "::"):
            path = path[len(protocol) + 2 :]
        path = path.rstrip("/")
        return path or cls.root_marker

    @staticmethod
    def _get_kwargs_from_urls(path: str) -> dict[str, Any]:
        return {}

    @classmethod
    def _parent(cls, path):
        path = cls._strip_protocol(path)
        if "/" in path:
            parent = path.rsplit("/", 1)[0].lstrip(cls.root_marker)
            return cls.root_marker + parent
        else:
            return cls.root_marker


class ProtocolConfig(TypedDict):
    netloc_is_anchor: set[str]
    supports_empty_parts: set[str]
    meaningful_trailing_slash: set[str]
    root_marker_override: dict[str, str]


class WrappedFileSystemFlavour(UPathParser):  # (pathlib_abc.FlavourBase)
    """flavour class for universal_pathlib

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
    #   workaround to be able to implement the flavour correctly.
    # TODO:
    #   These settings should be configured on the UPath class?!?
    protocol_config: ProtocolConfig = {
        "netloc_is_anchor": {
            "http",
            "https",
            "s3",
            "s3a",
            "smb",
            "gs",
            "gcs",
            "az",
            "adl",
            "abfs",
            "abfss",
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
        "root_marker_override": {
            "ssh": "/",
            "sftp": "/",
        },
    }

    def __init__(
        self,
        spec: type[AbstractFileSystem | FileSystemFlavourBase] | AbstractFileSystem,
        *,
        netloc_is_anchor: bool = False,
        supports_empty_parts: bool = False,
        meaningful_trailing_slash: bool = False,
        root_marker_override: str | None = None,
    ) -> None:
        """initialize the flavour with the given fsspec"""
        self._spec = spec

        # netloc is considered an anchor, influences:
        #   - splitdrive
        #   - join
        self.netloc_is_anchor = bool(netloc_is_anchor)

        # supports empty parts, influences:
        #   - join
        #   - UPath._parse_path
        self.supports_empty_parts = bool(supports_empty_parts)

        # meaningful trailing slash, influences:
        #   - join
        #   - UPath._parse_path
        self.has_meaningful_trailing_slash = bool(meaningful_trailing_slash)

        # some filesystems require UPath to enforce a specific root marker
        if root_marker_override is None:
            self.root_marker_override = None
        else:
            self.root_marker_override = str(root_marker_override)

    @classmethod
    @lru_cache(maxsize=None)
    def from_protocol(
        cls,
        protocol: str,
    ) -> WrappedFileSystemFlavour:
        """return the fsspec flavour for the given protocol"""

        _c = cls.protocol_config
        config: dict[str, Any] = {
            "netloc_is_anchor": protocol in _c["netloc_is_anchor"],
            "supports_empty_parts": protocol in _c["supports_empty_parts"],
            "meaningful_trailing_slash": protocol in _c["meaningful_trailing_slash"],
            "root_marker_override": _c["root_marker_override"].get(protocol),
        }

        # first try to get an already imported fsspec filesystem class
        try:
            return cls(class_registry[protocol], **config)
        except KeyError:
            pass
        # next try to get the flavour from the generated flavour registry
        # to avoid imports
        try:
            return cls(flavour_registry[protocol], **config)
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
        return cls(AnyProtocolFileSystemFlavour, **config)

    def __repr__(self):
        if isinstance(self._spec, type):
            return f"<wrapped class {self._spec.__name__}>"
        else:
            return f"<wrapped instance {self._spec.__class__.__name__}>"

    # === fsspec.AbstractFileSystem ===================================

    @property
    def protocol(self) -> tuple[str, ...]:
        if isinstance(self._spec.protocol, str):
            return (self._spec.protocol,)
        else:
            return self._spec.protocol

    @property
    def root_marker(self) -> str:
        if self.root_marker_override is not None:
            return self.root_marker_override
        else:
            return self._spec.root_marker

    @property
    def local_file(self) -> bool:
        return bool(getattr(self._spec, "local_file", False))

    @staticmethod
    def stringify_path(pth: JoinablePathLike) -> str:
        if isinstance(pth, str):
            out = pth
        elif isinstance(pth, upath.UPath) and not pth.is_absolute():
            out = str(pth)
        elif getattr(pth, "__fspath__", None) is not None:
            assert hasattr(pth, "__fspath__")
            out = pth.__fspath__()
        elif isinstance(pth, os.PathLike):
            out = str(pth)
        elif isinstance(pth, upath.UPath) and pth.is_absolute():
            out = pth.path
        else:
            out = str(pth)
        return normalize_empty_netloc(out)

    def strip_protocol(self, pth: JoinablePathLike) -> str:
        pth = self.stringify_path(pth)
        return self._spec._strip_protocol(pth)

    def get_kwargs_from_url(self, url: JoinablePathLike) -> dict[str, Any]:
        # NOTE: the public variant is _from_url not _from_urls
        if hasattr(url, "storage_options"):
            return dict(url.storage_options)
        url = self.stringify_path(url)
        return self._spec._get_kwargs_from_urls(url)

    def parent(self, path: JoinablePathLike) -> str:
        path = self.stringify_path(path)
        return self._spec._parent(path)

    # === pathlib_abc.FlavourBase =====================================

    @property
    def sep(self) -> str:  # type: ignore[override]
        return self._spec.sep

    @property
    def altsep(self) -> str | None:  # type: ignore[override]
        return None

    def isabs(self, path: JoinablePathLike) -> bool:
        path = self.strip_protocol(path)
        if self.local_file:
            return os.path.isabs(path)
        else:
            return path.startswith(self.root_marker)

    def join(self, path: JoinablePathLike, *paths: JoinablePathLike) -> str:
        if not paths:
            return self.strip_protocol(path) or self.root_marker
        if self.local_file:
            p = os.path.join(
                self.strip_protocol(path),
                *map(self.stringify_path, paths),
            )
            return p if os.name != "nt" else p.replace("\\", "/")
        if self.netloc_is_anchor:
            drv, p0 = self.splitdrive(path)
            pN = list(map(self.stringify_path, paths))
            if not drv and not p0:
                path, *pN = pN
                drv, p0 = self.splitdrive(path)
            p0 = p0 or self.sep
        else:
            p0 = str(self.strip_protocol(path)) or self.root_marker
            pN = list(map(self.stringify_path, paths))
            drv = ""
        if self.supports_empty_parts:
            return drv + self.sep.join([p0.removesuffix(self.sep), *pN])
        else:
            return drv + posixpath.join(p0, *pN)

    def split(self, path: JoinablePathLike) -> tuple[str, str]:
        stripped_path = self.strip_protocol(path)
        if self.local_file:
            return os.path.split(stripped_path)
        head = self.parent(stripped_path) or self.root_marker
        if head == self.sep:
            tail = stripped_path[1:]
        elif head:
            tail = stripped_path[len(head) + 1 :]
        else:
            tail = stripped_path
        if (
            not tail
            and not self.has_meaningful_trailing_slash
            and self.strip_protocol(head) != stripped_path
        ):
            return self.split(head)
        return head, tail

    def splitdrive(self, path: JoinablePathLike) -> tuple[str, str]:
        path = self.strip_protocol(path)
        if self.netloc_is_anchor:
            u = urlsplit(path)
            if u.scheme:
                # cases like: "http://example.com/foo/bar"
                drive = u._replace(path="", query="", fragment="").geturl()
                rest = u._replace(scheme="", netloc="").geturl()
                if (
                    u.path.startswith("//")
                    and SplitResult("", "", "//", "", "").geturl() == "////"
                ):
                    # see: fsspec/universal_pathlib#233
                    rest = rest[2:]
                return drive, rest or self.root_marker or self.sep
            else:
                # cases like: "bucket/some/special/key
                drive, root, tail = path.partition(self.sep)
                return drive, root + tail
        elif self.local_file:
            return os.path.splitdrive(path)
        else:
            # all other cases don't have a drive
            return "", path

    def normcase(self, path: JoinablePathLike) -> str:
        if self.local_file:
            return os.path.normcase(self.stringify_path(path))
        else:
            return self.stringify_path(path)

    def splitext(self, path: JoinablePathLike) -> tuple[str, str]:
        path = self.stringify_path(path)
        if self.local_file:
            return os.path.splitext(path)
        else:
            path, sep, name = path.rpartition(self.sep)
            if "." in name:
                stem, dot, ext = name.rpartition(".")
                suffix = dot + ext
            else:
                stem = name
                suffix = ""
            return path + sep + stem, suffix

    # === Python3.12 pathlib flavour ==================================

    def splitroot(self, path: JoinablePathLike) -> tuple[str, str, str]:
        drive, tail = self.splitdrive(path)
        if self.netloc_is_anchor:
            root_marker = self.root_marker or self.sep
        else:
            root_marker = self.root_marker
        return drive, root_marker, tail.removeprefix(self.sep)


default_flavour = WrappedFileSystemFlavour(AnyProtocolFileSystemFlavour)


class LazyFlavourDescriptor:
    """descriptor to lazily get the flavour for a given protocol"""

    def __init__(self) -> None:
        self._owner: type[UPath] | None = None

    def __set_name__(self, owner: type[UPath], name: str) -> None:
        # helper to provide a more informative repr
        self._owner = owner
        self._default_protocol: str | None
        try:
            self._default_protocol = self._owner.protocols[0]  # type: ignore
        except (AttributeError, IndexError):
            self._default_protocol = None

    def __get__(
        self, obj: UPath | None, objtype: type[UPath] | None = None
    ) -> WrappedFileSystemFlavour:
        if obj is not None:
            return WrappedFileSystemFlavour.from_protocol(
                obj._chain.active_path_protocol
            )
        elif self._default_protocol:  # type: ignore
            return WrappedFileSystemFlavour.from_protocol(self._default_protocol)
        else:
            return default_flavour

    def __repr__(self):
        cls_name = f"{type(self).__name__}"
        if self._owner is None:
            return f"<unbound {cls_name}>"
        else:
            return f"<{cls_name} of {self._owner.__name__}>"


def upath_strip_protocol(pth: JoinablePathLike) -> str:
    if protocol := get_upath_protocol(pth):
        return WrappedFileSystemFlavour.from_protocol(protocol).strip_protocol(pth)
    return WrappedFileSystemFlavour.stringify_path(pth)


def upath_get_kwargs_from_url(url: JoinablePathLike) -> dict[str, Any]:
    if protocol := get_upath_protocol(url):
        return WrappedFileSystemFlavour.from_protocol(protocol).get_kwargs_from_url(url)
    return {}


def upath_urijoin(base: str, uri: str) -> str:
    """Join a base URI and a possibly relative URI to form an absolute
    interpretation of the latter."""
    # see:
    #   https://github.com/python/cpython/blob/ae6c01d9d2/Lib/urllib/parse.py#L539-L605
    # modifications:
    #   - removed allow_fragments parameter
    #   - all schemes are considered to allow relative paths
    #   - all schemes are considered to allow netloc (revisit this)
    #   - no bytes support (removes encoding and decoding)
    if not base:
        return uri
    if not uri:
        return base

    bs = urlsplit(base, scheme="")
    us = urlsplit(uri, scheme=bs.scheme)

    if us.scheme != bs.scheme:  # or us.scheme not in uses_relative:
        return uri
    # if us.scheme in uses_netloc:
    if us.netloc:
        return us.geturl()
    else:
        us = us._replace(netloc=bs.netloc)
    # end if
    if not us.path and not us.fragment:
        us = us._replace(path=bs.path, fragment=bs.fragment)
        if not us.query:
            us = us._replace(query=bs.query)
        return us.geturl()

    base_parts = bs.path.split("/")
    if base_parts[-1] != "":
        del base_parts[-1]

    if us.path[:1] == "/":
        segments = us.path.split("/")
    else:
        segments = base_parts + us.path.split("/")
        segments[1:-1] = filter(None, segments[1:-1])

    resolved_path: list[str] = []

    for seg in segments:
        if seg == "..":
            try:
                resolved_path.pop()
            except IndexError:
                pass
        elif seg == ".":
            continue
        else:
            resolved_path.append(seg)

    if segments[-1] in (".", ".."):
        resolved_path.append("")

    return us._replace(path="/".join(resolved_path) or "/").geturl()
