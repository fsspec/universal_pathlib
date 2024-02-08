from __future__ import annotations

import ntpath
import os.path
import posixpath
import sys
import warnings
from functools import lru_cache
from functools import wraps
from typing import Any
from typing import Callable
from typing import Iterable
from typing import Union
from urllib.parse import urlsplit

if sys.version_info >= (3, 12):
    from typing import TypeAlias
else:
    TypeAlias = Any

from upath._compat import str_remove_prefix
from upath._compat import str_remove_suffix
from upath._protocol import get_upath_protocol
from upath._protocol import strip_upath_protocol

PathOrStr: TypeAlias = Union[str, "os.PathLike[str]"]

__all__ = [
    "FSSpecFlavour",
]


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

        # [py38-py312] _flavour.join is Callable[[list[str]], str]
        if isinstance(__path, (list, tuple)) and not paths:
            if not __path:
                return ""
            __path, *paths = __path  # type: ignore

        _path0: str = strip_upath_protocol(__path)
        _paths: Iterable[str] = map(strip_upath_protocol, paths)

        if self.join_like_urljoin:
            pth = str_remove_suffix(str(_path0), "/")
            sep = self.sep
            for b in _paths:
                if b.startswith(sep):
                    pth = b
                elif not pth:
                    pth += b
                else:
                    pth += sep + b
            joined = pth
        elif self.posixpath_only:
            joined = posixpath.join(_path0, *_paths)
        else:
            joined = os.path.join(_path0, *_paths)

        if self.join_prepends_protocol and (protocol := get_upath_protocol(__path)):
            joined = f"{protocol}://{joined}"

        return joined

    def splitroot(self, __path: PathOrStr) -> tuple[str, str, str]:
        """Split a path in the drive, the root and the rest."""
        if self.supports_fragments or self.supports_query_parameters:
            url = urlsplit(str(__path))
            drive = url._replace(path="", query="", fragment="").geturl()
            path = url._replace(scheme="", netloc="").geturl()
            # root = "/" if path.startswith("/") else ""
            root = "/"  # emulate upath.core.UPath < 3.12 behaviour
            return drive, root, str_remove_prefix(path, "/")

        if self.supports_netloc:
            path = strip_upath_protocol(__path, allow_unknown=True)
            protocol = get_upath_protocol(__path)
            if protocol:
                drive, root, tail = path.partition("/")
                return drive, root or "/", tail
            else:
                return "", "", path

        elif self.posixpath_only:
            path = strip_upath_protocol(__path, allow_unknown=True)
            return _get_splitroot(posixpath)(path)

        else:
            path = strip_upath_protocol(__path, allow_unknown=True)
            drv, root, path = _get_splitroot(os.path)(path)
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

    @_deprecated
    def parse_parts(self, parts):
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
    def join_parsed_parts(self, drv, root, parts, drv2, root2, parts2):
        """
        Join the two paths represented by the respective
        (drive, root, parts) tuples.  Return a new (drive, root, parts) tuple.
        """
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

    @_deprecated
    def casefold(self, s: str) -> str:
        """Casefold the string s."""
        if self.posixpath_only or os.name != "nt":
            return s
        else:
            return s.lower()


@lru_cache
def _get_splitroot(mod) -> Callable[[PathOrStr], tuple[str, str, str]]:
    """return the splitroot function from the given module"""
    if hasattr(mod, "splitroot"):
        return mod.splitroot

    elif mod is posixpath:

        def splitroot(p):
            p = os.fspath(p)
            sep = "/"
            empty = ""
            if p[:1] != sep:
                return empty, empty, p
            elif p[1:2] != sep or p[2:3] == sep:
                return empty, sep, p[1:]
            else:
                return empty, p[:2], p[2:]

        return splitroot

    elif mod is ntpath:

        def splitroot(p):
            p = os.fspath(p)
            sep = "\\"
            altsep = "/"
            colon = ":"
            unc_prefix = "\\\\?\\UNC\\"
            empty = ""
            normp = p.replace(altsep, sep)
            if normp[:1] == sep:
                if normp[1:2] == sep:
                    start = 8 if normp[:8].upper() == unc_prefix else 2
                    index = normp.find(sep, start)
                    if index == -1:
                        return p, empty, empty
                    index2 = normp.find(sep, index + 1)
                    if index2 == -1:
                        return p, empty, empty
                    return p[:index2], p[index2 : index2 + 1], p[index2 + 1 :]
                else:
                    return empty, p[:1], p[1:]
            elif normp[1:2] == colon:
                if normp[2:3] == sep:
                    return p[:2], p[2:3], p[3:]
                else:
                    return p[:2], empty, p[2:]
            else:
                return empty, empty, p

        return splitroot
    else:
        raise NotImplementedError(f"unsupported module: {mod!r}")
