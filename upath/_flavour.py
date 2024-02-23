from __future__ import annotations

import os.path
import posixpath
import sys
import warnings
from functools import lru_cache
from functools import wraps
from typing import TYPE_CHECKING
from typing import Any
from typing import Mapping
from typing import Sequence
from typing import Union
from urllib.parse import urlsplit

if sys.version_info >= (3, 12):
    from typing import TypeAlias
else:
    TypeAlias = Any

from fsspec.registry import known_implementations
from fsspec.registry import registry as class_registry
from fsspec.spec import AbstractFileSystem

from upath._compat import str_remove_prefix
from upath._compat import str_remove_suffix
from upath._flavour_sources import FileSystemFlavourBase
from upath._flavour_sources import flavour_registry
from upath._protocol import get_upath_protocol
from upath._protocol import normalize_empty_netloc

if TYPE_CHECKING:
    from upath.core import UPath

__all__ = [
    "LazyFlavourDescriptor",
    "default_flavour",
    "upath_urijoin",
    "upath_get_kwargs_from_url",
]

class_registry: Mapping[str, type[AbstractFileSystem]]
PathOrStr: TypeAlias = Union[str, "os.PathLike[str]"]


def _deprecated(func):
    if sys.version_info >= (3, 12):

        @wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(
                f"{func.__name__} is deprecated on py3.12",
                DeprecationWarning,
                stacklevel=2,
            )
            return func(*args, **kwargs)

        return wrapper
    else:
        return func


class AnyProtocolFileSystemFlavour(FileSystemFlavourBase):
    sep: str = "/"
    protocol: tuple[str, ...] = ()
    root_marker: str = "/"

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


class WrappedFileSystemFlavour:  # (pathlib_abc.FlavourBase)
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
    #
    _protocols_with_netloc_anchor = {
        "http",
        "https",
        "s3",
        "s3a",
        "gs",
        "gcs",
        "az",
        "adl",
        "abfs",
        "webdav+http",
        "webdav+https",
    }
    _protocols_with_empty_parts = {
        "http",
        "https",
        "s3",
        "s3a",
        "gs",
        "gcs",
        "az",
        "adl",
        "abfs",
    }
    _protocols_with_meaningful_trailing_slash = {
        "http",
        "https",
    }

    def __init__(
        self,
        spec: type[AbstractFileSystem | FileSystemFlavourBase] | AbstractFileSystem,
    ) -> None:
        """initialize the flavour with the given fsspec"""
        self._spec = spec

    @classmethod
    @lru_cache(maxsize=None)
    def from_protocol(
        cls,
        protocol: str,
    ) -> WrappedFileSystemFlavour:
        """return the fsspec flavour for the given protocol"""
        # first try to get an already imported fsspec filesystem class
        try:
            return cls(class_registry[protocol])
        except KeyError:
            pass
        # next try to get the flavour from the generated flavour registry
        # to avoid imports
        try:
            return cls(flavour_registry[protocol])
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
        return cls(AnyProtocolFileSystemFlavour)

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
        return self._spec.root_marker

    @property
    def netloc_is_anchor(self) -> bool:
        return bool(self._protocols_with_netloc_anchor.intersection(self.protocol))

    @property
    def supports_empty_parts(self) -> bool:
        return bool(self._protocols_with_empty_parts.intersection(self.protocol))

    @property
    def has_meaningful_trailing_slash(self) -> bool:
        return bool(
            self._protocols_with_meaningful_trailing_slash.intersection(self.protocol)
        )

    @property
    def local_file(self) -> bool:
        return bool(getattr(self._spec, "local_file", False))

    @staticmethod
    def stringify_path(pth: PathOrStr) -> str:
        if isinstance(pth, str):
            out = pth
        elif getattr(pth, "__fspath__", None) is not None:
            out = pth.__fspath__()
        elif isinstance(pth, os.PathLike):
            out = str(pth)
        elif hasattr(pth, "path"):
            out = pth.path
        else:
            out = str(pth)
        return normalize_empty_netloc(out)

    def empty_part_join(self, path: str, *paths: str) -> str:
        sep = self.sep
        return sep.join([str_remove_suffix(path, sep), *paths])

    def strip_protocol(self, pth: PathOrStr) -> str:
        pth = self.stringify_path(pth)
        return self._spec._strip_protocol(pth)

    def get_kwargs_from_url(self, url: PathOrStr) -> dict[str, Any]:
        # NOTE: the public variant is _from_url not _from_urls
        if hasattr(url, "storage_options"):
            return dict(url.storage_options)
        url = self.stringify_path(url)
        return self._spec._get_kwargs_from_urls(url)

    def parent(self, path: PathOrStr) -> str:
        path = self.stringify_path(path)
        return self._spec._parent(path)

    # === pathlib_abc.FlavourBase =====================================

    @property
    def sep(self) -> str:
        return self._spec.sep

    @property
    def altsep(self) -> str | None:
        return None

    def isabs(self, path: PathOrStr) -> bool:
        return self.strip_protocol(path).startswith(self.root_marker)

    def join(self, path: PathOrStr, *paths: PathOrStr) -> str:
        if self.supports_empty_parts:
            _join = self.empty_part_join
        else:
            _join = posixpath.join
        if self.netloc_is_anchor:
            drv, p0 = self.splitdrive(path)
            pN = list(map(self.stringify_path, paths))
            if not drv and not p0:
                path, *pN = pN
                drv, p0 = self.splitdrive(path)
            return drv + _join(p0 or self.sep, *pN)
        else:
            p0 = str(self.strip_protocol(path))
            pN = map(self.stringify_path, paths)
            return _join(p0, *pN)

    def split(self, path: PathOrStr):
        stripped_path = self.strip_protocol(path)
        head = self.parent(stripped_path) or self.root_marker
        if head:
            return head, stripped_path[len(head) + 1 :]
        else:
            return "", stripped_path

    def splitdrive(self, path: PathOrStr) -> tuple[str, str]:
        path = self.strip_protocol(path)
        if self.netloc_is_anchor:
            u = urlsplit(path)
            if u.scheme:
                # cases like: "http://example.com/foo/bar"
                drive = u._replace(path="", query="", fragment="").geturl()
                rest = u._replace(scheme="", netloc="").geturl()
                return drive, rest or self.root_marker or self.sep
            else:
                # cases like: "bucket/some/special/key
                drive, root, tail = path.partition(self.sep)
                return drive, root + tail
        else:
            # all other cases don't have a drive
            return "", path

    def normcase(self, path: PathOrStr) -> str:
        if self.local_file:
            return os.path.normcase(self.stringify_path(path))
        else:
            return self.stringify_path(path)

    # === Python3.12 pathlib flavour ==================================

    def splitroot(self, path: PathOrStr) -> tuple[str, str, str]:
        drive, tail = self.splitdrive(path)
        if self.netloc_is_anchor:
            root_marker = self.root_marker or self.sep
        else:
            root_marker = self.root_marker
        return drive, root_marker, str_remove_prefix(tail, self.sep)

    # === deprecated backwards compatibility ===========================

    @_deprecated
    def casefold(self, s: str) -> str:
        if self.local_file:
            return s
        else:
            return s.lower()

    @_deprecated
    def parse_parts(self, parts: Sequence[str]) -> tuple[str, str, list[str]]:
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

    @_deprecated
    def join_parsed_parts(
        self,
        drv: str,
        root: str,
        parts: list[str],
        drv2: str,
        root2: str,
        parts2: list[str],
    ) -> tuple[str, str, list[str]]:
        if root2:
            if not drv2 and drv:
                return drv, root2, [drv + root2] + parts2[1:]
        elif drv2:
            if drv2 == drv or self.casefold(drv2) == self.casefold(drv):
                # Same drive => second path is relative to the first
                return drv, root, parts + parts2[1:]
        else:
            # Second path is non-anchored (common case)
            return drv, root, parts + parts2
        return drv2, root2, parts2


default_flavour = WrappedFileSystemFlavour(AnyProtocolFileSystemFlavour)


class LazyFlavourDescriptor:
    """descriptor to lazily get the flavour for a given protocol"""

    def __init__(self) -> None:
        self._owner = None

    def __set_name__(self, owner: type[UPath], name: str) -> None:
        # helper to provide a more informative repr
        self._owner = owner
        try:
            self._default_protocol = self._owner.protocols[0]
        except (AttributeError, IndexError):
            self._default_protocol = None

    def __get__(self, instance: UPath, owner: type[UPath]) -> WrappedFileSystemFlavour:
        if instance is not None:
            return WrappedFileSystemFlavour.from_protocol(instance.protocol)
        elif self._default_protocol:
            return WrappedFileSystemFlavour.from_protocol(self._default_protocol)
        else:
            return default_flavour

    def __repr__(self):
        cls_name = f"{type(self).__name__}"
        if self._owner is None:
            return f"<unbound {cls_name}>"
        else:
            return f"<{cls_name} of {self._owner.__name__}>"


def upath_strip_protocol(pth: PathOrStr) -> str:
    if protocol := get_upath_protocol(pth):
        return WrappedFileSystemFlavour.from_protocol(protocol).strip_protocol(pth)
    return WrappedFileSystemFlavour.stringify_path(pth)


def upath_get_kwargs_from_url(url: PathOrStr) -> dict[str, Any]:
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

    resolved_path = []

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
