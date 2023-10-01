from __future__ import annotations

import ntpath
import os
import posixpath
import re
import sys
import warnings
from copy import copy
from pathlib import Path
from pathlib import PurePath
from typing import Any
from typing import Self
from typing import TypeAlias
from urllib.parse import urlsplit

from fsspec import AbstractFileSystem
from fsspec import filesystem
from fsspec import get_filesystem_class
from fsspec.core import split_protocol as fsspec_split_protocol
from fsspec.core import strip_protocol as fsspec_strip_protocol

from upath.registry import get_upath_class

PathOrStr: TypeAlias = "str | PurePath | os.PathLike"


class fsspecpathmod:
    sep: str = "/"
    altsep: str | None = None

    @staticmethod
    def join(__path: PathOrStr, *paths: PathOrStr) -> str:
        return posixpath.join(*map(strip_upath_protocol, [__path, *paths]))

    @staticmethod
    def splitroot(__path: PathOrStr) -> tuple[str, str, str]:
        path = strip_upath_protocol(__path)
        return posixpath.splitroot(path)

    @staticmethod
    def splitdrive(__path: PathOrStr) -> tuple[str, str]:
        path = strip_upath_protocol(__path)
        return posixpath.splitdrive(path)

    @staticmethod
    def normcase(__path: PathOrStr) -> str:
        return posixpath.normcase(__path)


_PROTOCOL_RE = re.compile(
    r"^(?P<protocol>[A-Za-z][A-Za-z0-9+]+):(?P<slashes>//?)(?P<path>.*)"
)

def split_upath_protocol(pth: str) -> str:
    if m := _PROTOCOL_RE.match(pth):
        return m.group("protocol")
    return ""


def strip_upath_protocol(pth: str) -> str:
    if m := _PROTOCOL_RE.match(pth):
        protocol = m.group("protocol")
        path = m.group("path")
        if len(m.group("slashes")) == 1:
            pth = f"{protocol}:///{path}"
        return fsspec_strip_protocol(pth)
    else:
        return pth

def get_upath_protocol(
    pth: str | PurePath,
    *,
    protocol: str | None = None,
    storage_options: dict[str, Any] | None = None,
) -> str:
    """return the filesystem spec protocol"""
    if isinstance(pth, str):
        pth_protocol = split_upath_protocol(pth)
    elif isinstance(pth, UPath):
        pth_protocol = pth.protocol
    elif isinstance(pth, PurePath):
        pth_protocol = ""
    else:
        raise TypeError("expected a str or PurePath instance")
    # if storage_options and not protocol:
    #     protocol = "file"
    if protocol and pth_protocol and protocol != pth_protocol:
        raise TypeError(
            f"requested protocol {protocol!r} incompatible with {pth_protocol!r}"
        )
    return protocol or pth_protocol or ""


def _get_pathmod(arg: PurePath) -> fsspecpathmod:
    try:
        return arg.pathmod  # type: ignore
    except AttributeError:
        return arg._flavour  # type: ignore


class UPath(Path):
    __slots__ = (
        "_protocol",
        "_storage_options",
        "_fs_cached",
    )
    pathmod = _flavour = fsspecpathmod

    # --- Path.__new__
    # def __new__(cls, *args, **kwargs):
    #     if cls is Path:
    #         cls = WindowsPath if os.name == 'nt' else PosixPath
    #     return object.__new__(cls)

    def __new__(cls, *args, protocol: str | None = None, **storage_options: Any) -> Self:
        # fill empty arguments
        if not args:
            args = ".",

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

        obj = object.__new__(upath_cls)
        obj._protocol = pth_protocol
        return obj

    # --- PurePath.__init__
    #   def __init__(self, *args):
    #       paths = []
    #       for arg in args:
    #           if isinstance(arg, PurePath):
    #               if arg._flavour is ntpath and self._flavour is posixpath:
    #                   # GH-103631: Convert separators for backwards compatibility.
    #                   paths.extend(path.replace('\\', '/') for path in arg._raw_paths)
    #               else:
    #                   paths.extend(arg._raw_paths)
    #           else:
    #               try:
    #                   path = os.fspath(arg)
    #               except TypeError:
    #                   path = arg
    #               if not isinstance(path, str):
    #                   raise TypeError(
    #                       "argument should be a str or an os.PathLike "
    #                       "object where __fspath__ returns a str, "
    #                       f"not {type(path).__name__!r}")
    #               paths.append(path)
    #       self._raw_paths = paths
    #
    # --- Path.__init__
    # def __init__(self, *args, **kwargs):
    #     if kwargs:
    #         msg = ("support for supplying keyword arguments to pathlib.PurePath "
    #                "is deprecated and scheduled for removal in Python {remove}")
    #         warnings._deprecated("pathlib.PurePath(**kwargs)", msg, remove=(3, 14))
    #     super().__init__(*args)

    def __init__(self, *args, protocol: str | None = None, **storage_options: Any) -> None:
        # handle deprecated arguments
        if "netloc" in storage_options:
            raise NotImplementedError  # todo ...

        # retrieve storage_options
        if args:
            args0 = args[0]
            if isinstance(args0, UPath):
                self._storage_options = args0.storage_options
            else:
                fs_cls: type[AbstractFileSystem] = get_filesystem_class(self._protocol)
                pth_storage_options = fs_cls._get_kwargs_from_urls(str(args0))
                self._storage_options = {**pth_storage_options, **storage_options}
        else:
            self._storage_options = storage_options.copy()

        # check that UPath subclasses in args are compatible
        # --> ensures items in _raw_paths are compatible
        for arg in args:
            if not isinstance(arg, UPath):
                continue
            # protcols: only identical (or empty "") protocols can combine
            if arg.protocol and arg.protocol != self._protocol:
                raise TypeError(
                    "can't combine different UPath protocols as parts"
                )
            # storage_options: args may not define other storage_options
            if any(
                self._storage_options.get(key) != value
                for key, value in arg.storage_options.items()
            ):
                raise ValueError(
                    "can't combine different UPath storage_options as parts"
                )

        # fill ._raw_paths
        super().__init__(*args)

    # === upath.UPath only ============================================

    @property
    def protocol(self) -> str:
        return self._protocol

    @property
    def storage_options(self) -> dict[str, Any]:
        return self._storage_options

    @property
    def fs(self) -> AbstractFileSystem:
        try:
            return self._fs_cached
        except AttributeError:
            fs = self._fs_cached = filesystem(
                protocol=self._protocol, **self._storage_options
            )
            return fs

    @property
    def path(self) -> str:
        return self._format_parsed_parts(
            self.drive, self.root, self._tail
        ) or '.'

    @property
    def _kwargs(self):
        warnings.warn(
            "use UPath.storage_options instead of UPath._kwargs",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.storage_options

    @property
    def _url(self):
        return urlsplit(str(self))

    # === pathlib.PurePath ============================================

    def __reduce__(self):
        state = {
            "_protocol": self._protocol,
            "_storage_options": self._storage_options,
        }
        return (self.__class__, tuple(self._raw_paths), (None, state))

    def with_segments(self, *pathsegments):
        return type(self)(
            *pathsegments,
            protocol=self._protocol,
            **self._storage_options,
        )

    #   @classmethod
    #   def _parse_path(cls, path):
    #       if not path:
    #           return '', '', []
    #       sep = cls._flavour.sep
    #       altsep = cls._flavour.altsep
    #       if altsep:
    #           path = path.replace(altsep, sep)
    #       drv, root, rel = cls._flavour.splitroot(path)
    #       if not root and drv.startswith(sep) and not drv.endswith(sep):
    #           drv_parts = drv.split(sep)
    #           if len(drv_parts) == 4 and drv_parts[2] not in '?.':
    #               # e.g. //server/share
    #               root = sep
    #           elif len(drv_parts) == 6:
    #               # e.g. //?/unc/server/share
    #               root = sep
    #       parsed = [sys.intern(str(x)) for x in rel.split(sep) if x and x != '.']
    #       return drv, root, parsed

    # def _load_parts(self):
    #     paths = self._raw_paths
    #     if len(paths) == 0:
    #         path = ''
    #     elif len(paths) == 1:
    #         path = paths[0]
    #     else:
    #         path = self._flavour.join(*paths)
    #     drv, root, tail = self._parse_path(path)
    #     self._drv = drv
    #     self._root = root
    #     self._tail_cached = tail

    #   def _from_parsed_parts(self, drv, root, tail):
    #       path_str = self._format_parsed_parts(drv, root, tail)
    #       path = self.with_segments(path_str)
    #       path._str = path_str or '.'
    #       path._drv = drv
    #       path._root = root
    #       path._tail_cached = tail
    #       return path

    # @classmethod
    # def _format_parsed_parts(cls, drv, root, tail):
    #     if drv or root:
    #         return drv + root + cls._flavour.sep.join(tail)
    #     elif tail and cls._flavour.splitdrive(tail[0])[0]:
    #         tail = ['.'] + tail
    #     return cls._flavour.sep.join(tail)

    def __str__(self):
        try:
            return self._str
        except AttributeError:
            path = self._format_parsed_parts(
                self.drive, self.root, self._tail
            ) or '.'
            # self._str = get_filesystem_class(self._protocol).unstrip_protocol(path)
            if self._protocol:
                self._str = f"{self._protocol}://{path}"
            else:
                self._str = path
            return self._str

    def __fspath__(self):
        msg = (
            "in a future version of UPath this will be set to None"
            " unless the filesystem is local (or caches locally)"
        )
        warnings.warn(msg, PendingDeprecationWarning, stacklevel=2)
        return str(self)

    # def as_posix(self):
    #     f = self._flavour
    #     return str(self).replace(f.sep, '/')

    def __bytes__(self):
        msg = (
            "in a future version of UPath this will be set to None"
            " unless the filesystem is local (or caches locally)"
        )
        warnings.warn(msg, PendingDeprecationWarning, stacklevel=2)
        return os.fsencode(self)

    # def __repr__(self):
    #     return "{}({!r})".format(self.__class__.__name__, self.as_posix())

    def as_uri(self):
        return str(self)

    # @property
    # def _str_normcase(self):
    #     try:
    #         return self._str_normcase_cached
    #     except AttributeError:
    #         if _is_case_sensitive(self._flavour):
    #             self._str_normcase_cached = str(self)
    #         else:
    #             self._str_normcase_cached = str(self).lower()
    #         return self._str_normcase_cached

    # @property
    # def _parts_normcase(self):
    #     # Cached parts with normalized case, for comparisons.
    #     try:
    #         return self._parts_normcase_cached
    #     except AttributeError:
    #         self._parts_normcase_cached = self._str_normcase.split(self._flavour.sep)
    #         return self._parts_normcase_cached

    # @property
    # def _lines(self):
    #     # Path with separators and newlines swapped, for pattern matching.
    #     try:
    #         return self._lines_cached
    #     except AttributeError:
    #         path_str = str(self)
    #         if path_str == '.':
    #             self._lines_cached = ''
    #         else:
    #             trans = _SWAP_SEP_AND_NEWLINE[self._flavour.sep]
    #             self._lines_cached = path_str.translate(trans)
    #         return self._lines_cached

    # def __eq__(self, other):
    #     if not isinstance(other, PurePath):
    #         return NotImplemented
    #     return self._str_normcase == other._str_normcase and self._flavour is other._flavour

    # def __hash__(self):
    #     try:
    #         return self._hash
    #     except AttributeError:
    #         self._hash = hash(self._str_normcase)
    #         return self._hash

    # def __lt__(self, other):
    #     if not isinstance(other, PurePath) or self._flavour is not other._flavour:
    #         return NotImplemented
    #     return self._parts_normcase < other._parts_normcase

    # def __le__(self, other):
    #     if not isinstance(other, PurePath) or self._flavour is not other._flavour:
    #         return NotImplemented
    #     return self._parts_normcase <= other._parts_normcase

    # def __gt__(self, other):
    #     if not isinstance(other, PurePath) or self._flavour is not other._flavour:
    #         return NotImplemented
    #     return self._parts_normcase > other._parts_normcase

    # def __ge__(self, other):
    #     if not isinstance(other, PurePath) or self._flavour is not other._flavour:
    #         return NotImplemented
    #     return self._parts_normcase >= other._parts_normcase

    #   @property
    #   def drive(self):
    #       try:
    #           return self._drv
    #       except AttributeError:
    #           self._load_parts()
    #           return self._drv

    #   @property
    #   def root(self):
    #       """The root of the path, if any."""
    #       try:
    #           return self._root
    #       except AttributeError:
    #           self._load_parts()
    #           return self._root

    #   @property
    #   def _tail(self):
    #       try:
    #           return self._tail_cached
    #       except AttributeError:
    #           self._load_parts()
    #           return self._tail_cached

    #   @property
    #   def anchor(self):
    #       """The concatenation of the drive and root, or ''."""
    #       anchor = self.drive + self.root
    #       return anchor


    # @property
    # def name(self):
    #     """The final path component, if any."""
    #     tail = self._tail
    #     if not tail:
    #         return ''
    #     return tail[-1]

    # @property
    # def suffix(self):
    #     name = self.name
    #     i = name.rfind('.')
    #     if 0 < i < len(name) - 1:
    #         return name[i:]
    #     else:
    #         return ''

    # @property
    # def suffixes(self):
    #     name = self.name
    #     if name.endswith('.'):
    #         return []
    #     name = name.lstrip('.')
    #     return ['.' + suffix for suffix in name.split('.')[1:]]

    # @property
    # def stem(self):
    #     name = self.name
    #     i = name.rfind('.')
    #     if 0 < i < len(name) - 1:
    #         return name[:i]
    #     else:
    #         return name

    #   def with_name(self, name):
    #       if not self.name:
    #           raise ValueError("%r has an empty name" % (self,))
    #       f = self._flavour
    #       drv, root, tail = f.splitroot(name)
    #       if drv or root or not tail or f.sep in tail or (f.altsep and f.altsep in tail):
    #           raise ValueError("Invalid name %r" % (name))
    #       return self._from_parsed_parts(self.drive, self.root,
    #                                      self._tail[:-1] + [name])

    # def with_stem(self, stem):
    #     return self.with_name(stem + self.suffix)

    #   def with_suffix(self, suffix):
    #       f = self._flavour
    #       if f.sep in suffix or f.altsep and f.altsep in suffix:
    #           raise ValueError("Invalid suffix %r" % (suffix,))
    #       if suffix and not suffix.startswith('.') or suffix == '.':
    #           raise ValueError("Invalid suffix %r" % (suffix))
    #       name = self.name
    #       if not name:
    #           raise ValueError("%r has an empty name" % (self,))
    #       old_suffix = self.suffix
    #       if not old_suffix:
    #           name = name + suffix
    #       else:
    #           name = name[:-len(old_suffix)] + suffix
    #       return self._from_parsed_parts(self.drive, self.root,
    #                                      self._tail[:-1] + [name])

    #   def relative_to(self, other, /, *_deprecated, walk_up=False):
    #       if _deprecated:
    #           msg = ("support for supplying more than one positional argument "
    #                  "to pathlib.PurePath.relative_to() is deprecated and "
    #                  "scheduled for removal in Python {remove}")
    #           warnings._deprecated("pathlib.PurePath.relative_to(*args)", msg,
    #                                remove=(3, 14))
    #       other = self.with_segments(other, *_deprecated)
    #       for step, path in enumerate([other] + list(other.parents)):
    #           if self.is_relative_to(path):
    #               break
    #           elif not walk_up:
    #               raise ValueError(f"{str(self)!r} is not in the subpath of {str(other)!r}")
    #           elif path.name == '..':
    #               raise ValueError(f"'..' segment in {str(other)!r} cannot be walked")
    #       else:
    #           raise ValueError(f"{str(self)!r} and {str(other)!r} have different anchors")
    #       parts = ['..'] * step + self._tail[len(path._tail):]
    #       return self.with_segments(*parts)

    # def is_relative_to(self, other, /, *_deprecated):
    #     if _deprecated:
    #         msg = ("support for supplying more than one argument to "
    #                "pathlib.PurePath.is_relative_to() is deprecated and "
    #                "scheduled for removal in Python {remove}")
    #         warnings._deprecated("pathlib.PurePath.is_relative_to(*args)",
    #                              msg, remove=(3, 14))
    #     other = self.with_segments(other, *_deprecated)
    #     return other == self or other in self.parents

    #   @property
    #   def parts(self):
    #       if self.drive or self.root:
    #           return (self.drive + self.root,) + tuple(self._tail)
    #       else:
    #           return tuple(self._tail)

    # def joinpath(self, *pathsegments):
    #     return self.with_segments(self, *pathsegments)

    # def __truediv__(self, key):
    #     try:
    #         return self.joinpath(key)
    #     except TypeError:
    #         return NotImplemented

    # def __rtruediv__(self, key):
    #     try:
    #         return self.with_segments(key, self)
    #     except TypeError:
    #         return NotImplemented

    #   @property
    #   def parent(self):
    #       drv = self.drive
    #       root = self.root
    #       tail = self._tail
    #       if not tail:
    #           return self
    #       return self._from_parsed_parts(drv, root, tail[:-1])

    # @property
    # def parents(self):
    #     return _PathParents(self)

    #   def is_absolute(self):
    #       if self._flavour is ntpath:
    #           # ntpath.isabs() is defective - see GH-44626.
    #           return bool(self.drive and self.root)
    #       elif self._flavour is posixpath:
    #           # Optimization: work with raw paths on POSIX.
    #           for path in self._raw_paths:
    #               if path.startswith('/'):
    #                   return True
    #           return False
    #       else:
    #           return self._flavour.isabs(str(self))

    def is_reserved(self):
        # if self._flavour is posixpath or not self._tail:
        #     return False
        # if self.drive.startswith('\\\\'):
        #     # UNC paths are never reserved.
        #     return False
        # name = self._tail[-1].partition('.')[0].partition(':')[0].rstrip(' ')
        # return name.upper() in _WIN_RESERVED_NAMES
        return False

    #   def match(self, path_pattern, *, case_sensitive=None):
    #       if not isinstance(path_pattern, PurePath):
    #           path_pattern = self.with_segments(path_pattern)
    #       if case_sensitive is None:
    #           case_sensitive = _is_case_sensitive(self._flavour)
    #       pattern = _compile_pattern_lines(path_pattern._lines, case_sensitive)
    #       if path_pattern.drive or path_pattern.root:
    #           return pattern.match(self._lines) is not None
    #       elif path_pattern._tail:
    #           return pattern.search(self._lines) is not None
    #       else:
    #           raise ValueError("empty pattern")

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
        # return self._flavour.ismount(self)
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
        # return self._flavour.isjunction(self)
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
        #   st = self.stat()
        #   try:
        #       other_st = other_path.stat()
        #   except AttributeError:
        #       other_st = self.with_segments(other_path).stat()
        #   return self._flavour.samestat(st, other_st)
        raise NotImplementedError

    def open(self, mode='r', buffering=-1, encoding=None,
             errors=None, newline=None):
        return self.fs.open(self.path, mode)  # fixme

    # def read_bytes(self):
    #     with self.open(mode='rb') as f:
    #         return f.read()

    # def read_text(self, encoding=None, errors=None):
    #     encoding = io.text_encoding(encoding)
    #     with self.open(mode='r', encoding=encoding, errors=errors) as f:
    #         return f.read()

    # def write_bytes(self, data):
    #     view = memoryview(data)
    #     with self.open(mode='wb') as f:
    #         return f.write(view)

    # def write_text(self, data, encoding=None, errors=None, newline=None):
    #     if not isinstance(data, str):
    #         raise TypeError('data must be str, not %s' %
    #                         data.__class__.__name__)
    #     encoding = io.text_encoding(encoding)
    #     with self.open(mode='w', encoding=encoding, errors=errors, newline=newline) as f:
    #         return f.write(data)

    def iterdir(self):
        # for name in os.listdir(self):
        #     yield self._make_child_relpath(name)
        for name in self.fs.listdir(self.path):
            # fsspec returns dictionaries
            if isinstance(name, dict):
                name = name.get("name")
            if name in {".", ".."}:
                # Yielding a path object for these makes little sense
                continue
            # only want the path name with iterdir
            _, _, name = name.rpartition(self._flavour.sep)
            yield self._make_child_relpath(name)

    def _scandir(self):
        # return os.scandir(self)
        raise NotImplementedError

    # def _make_child_relpath(self, name):
    #     path = super()._make_child_relpath(name)
    #     path._fs_cached = self._fs_cached
    #     return path

    # def glob(self, pattern, *, case_sensitive=None):
    #     sys.audit("pathlib.Path.glob", self, pattern)
    #     if not pattern:
    #         raise ValueError("Unacceptable pattern: {!r}".format(pattern))
    #     drv, root, pattern_parts = self._parse_path(pattern)
    #     if drv or root:
    #         raise NotImplementedError("Non-relative patterns are unsupported")
    #     if pattern[-1] in (self._flavour.sep, self._flavour.altsep):
    #         pattern_parts.append('')
    #     selector = _make_selector(tuple(pattern_parts), self._flavour, case_sensitive)
    #     for p in selector.select_from(self):
    #         yield p

    def glob(self, pattern: str, *, case_sensitive=None):
        path_pattern = self.joinpath(pattern).path
        for name in self.fs.glob(path_pattern):
            name = name.removeprefix(self.path)
            _, _, name = name.partition(self._flavour.sep)
            yield self.joinpath(name)

    # def rglob(self, pattern, *, case_sensitive=None):
    #     sys.audit("pathlib.Path.rglob", self, pattern)
    #     drv, root, pattern_parts = self._parse_path(pattern)
    #     if drv or root:
    #         raise NotImplementedError("Non-relative patterns are unsupported")
    #     if pattern and pattern[-1] in (self._flavour.sep, self._flavour.altsep):
    #         pattern_parts.append('')
    #     selector = _make_selector(("**",) + tuple(pattern_parts), self._flavour, case_sensitive)
    #     for p in selector.select_from(self):
    #         yield p

    def rglob(self, pattern: str, *, case_sensitive=None):
        r_path_pattern = self.joinpath("**", pattern).path
        for name in self.fs.glob(r_path_pattern):
            name = name.removeprefix(self.path)
            _, _, name = name.partition(self._flavour.sep)
            yield self.joinpath(name)

    # def walk(self, top_down=True, on_error=None, follow_symlinks=False):
    #     sys.audit("pathlib.Path.walk", self, on_error, follow_symlinks)
    #     paths = [self]
    #     while paths:
    #         path = paths.pop()
    #         if isinstance(path, tuple):
    #             yield path
    #             continue
    #         try:
    #             scandir_it = path._scandir()
    #         except OSError as error:
    #             if on_error is not None:
    #                 on_error(error)
    #             continue
    #         with scandir_it:
    #             dirnames = []
    #             filenames = []
    #             for entry in scandir_it:
    #                 try:
    #                     is_dir = entry.is_dir(follow_symlinks=follow_symlinks)
    #                 except OSError:
    #                     # Carried over from os.path.isdir().
    #                     is_dir = False
    #                 if is_dir:
    #                     dirnames.append(entry.name)
    #                 else:
    #                     filenames.append(entry.name)
    #         if top_down:
    #             yield path, dirnames, filenames
    #         else:
    #             paths.append((path, dirnames, filenames))
    #         paths += [path._make_child_relpath(d) for d in reversed(dirnames)]

    # def __enter__(self):
    #     warnings.warn("pathlib.Path.__enter__() is deprecated and scheduled "
    #                   "for removal in Python 3.13; Path objects as a context "
    #                   "manager is a no-op",
    #                   DeprecationWarning, stacklevel=2)
    #     return self

    # def __exit__(self, t, v, tb):
    #     pass

    # Public API

    @classmethod
    def cwd(cls):
        # return cls().absolute()
        if cls is UPath:
            return get_upath_class("").cwd()
        else:
            raise NotImplementedError

    @classmethod
    def home(cls):
        # return cls("~").expanduser()
        if cls is UPath:
            return get_upath_class("").home()
        else:
            raise NotImplementedError

    def absolute(self):
        # if self.is_absolute():
        #     return self
        # elif self.drive:
        #     # There is a CWD on each drive-letter drive.
        #     cwd = self._flavour.abspath(self.drive)
        # else:
        #     cwd = os.getcwd()
        #     if not self.root and not self._tail:
        #         result = self.with_segments(cwd)
        #         result._str = cwd
        #         return result
        # return self.with_segments(cwd, self)
        return self

    def resolve(self, strict=False):
        # def check_eloop(e):
        #     winerror = getattr(e, 'winerror', 0)
        #     if e.errno == ELOOP or winerror == _WINERROR_CANT_RESOLVE_FILENAME:
        #         raise RuntimeError("Symlink loop from %r" % e.filename)
        # try:
        #     s = self._flavour.realpath(self, strict=strict)
        # except OSError as e:
        #     check_eloop(e)
        #     raise
        # p = self.with_segments(s)
        # if not strict:
        #     try:
        #         p.stat()
        #     except OSError as e:
        #         check_eloop(e)
        # return p
        _parts = self.parts

        # Do not attempt to normalize path if no parts are dots
        if ".." not in _parts and "." not in _parts:
            return self

        resolved: list[str] = []
        resolvable_parts = _parts[1:]
        for i, part in enumerate(resolvable_parts):
            if part == "..":
                if resolved:
                    resolved.pop()
            elif part != ".":
                resolved.append(part)

        return self.with_segments(*_parts[:1], *resolved)

    def owner(self):
        # try:
        #     import pwd
        #     return pwd.getpwuid(self.stat().st_uid).pw_name
        # except ImportError:
        #     raise NotImplementedError("Path.owner() is unsupported on this system")
        raise NotImplementedError

    def group(self):
        # try:
        #     import grp
        #     return grp.getgrgid(self.stat().st_gid).gr_name
        # except ImportError:
        #     raise NotImplementedError("Path.group() is unsupported on this system")
        raise NotImplementedError

    def readlink(self):
        # if not hasattr(os, "readlink"):
        #     raise NotImplementedError("os.readlink() not available on this system")
        # return self.with_segments(os.readlink(self))
        raise NotImplementedError

    def touch(self, mode=0o666, exist_ok=True):
        # if exist_ok:
        #     try:
        #         os.utime(self, None)
        #     except OSError:
        #         # Avoid exception chaining
        #         pass
        #     else:
        #         return
        # flags = os.O_CREAT | os.O_WRONLY
        # if not exist_ok:
        #     flags |= os.O_EXCL
        # fd = os.open(self, flags, mode)
        # os.close(fd)
        self.fs.touch(self.path, truncate=not exist_ok)

    def mkdir(self, mode=0o777, parents=False, exist_ok=False):
        # try:
        #     os.mkdir(self, mode)
        # except FileNotFoundError:
        #     if not parents or self.parent == self:
        #         raise
        #     self.parent.mkdir(parents=True, exist_ok=True)
        #     self.mkdir(mode, parents=False, exist_ok=exist_ok)
        # except OSError:
        #     # Cannot rely on checking for EEXIST, since the operating system
        #     # could give priority to other errors like EACCES or EROFS
        #     if not exist_ok or not self.is_dir():
        #         raise
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
        # os.chmod(self, mode, follow_symlinks=follow_symlinks)
        raise NotImplementedError

    # def lchmod(self, mode):
    #     self.chmod(mode, follow_symlinks=False)

    def unlink(self, missing_ok=False):
        # try:
        #     os.unlink(self)
        # except FileNotFoundError:
        #     if not missing_ok:
        #         raise
        if not self.exists():
            if not missing_ok:
                raise FileNotFoundError(str(self))
            return
        self.fs.rm(self.path, recursive=False)

    def rmdir(self, recursive: bool = True):  # fixme: non-standard
    # def rmdir(self):
        # os.rmdir(self)
        if not self.is_dir():
            raise NotADirectoryError(str(self))
        if not recursive and next(self.iterdir()):
            raise OSError(f"Not recursive and directory not empty: {self}")
        self.fs.rm(self.path, recursive=recursive)

    def rename(self, target, *, recursive=False, maxdepth=None, **kwargs):
    # def rename(self, target):
        # os.rename(self, target)
        # return self.with_segments(target)
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
        # os.replace(self, target)
        # return self.with_segments(target)
        raise NotImplementedError

    def symlink_to(self, target, target_is_directory=False):
        # if not hasattr(os, "symlink"):
        #     raise NotImplementedError("os.symlink() not available on this system")
        # os.symlink(target, self, target_is_directory)
        raise NotImplementedError

    def hardlink_to(self, target):
        # if not hasattr(os, "link"):
        #     raise NotImplementedError("os.link() not available on this system")
        # os.link(target, self)
        raise NotImplementedError

    def expanduser(self):
        # if (not (self.drive or self.root) and
        #         self._tail and self._tail[0][:1] == '~'):
        #     homedir = self._flavour.expanduser(self._tail[0])
        #     if homedir[:1] == "~":
        #         raise RuntimeError("Could not determine home directory.")
        #     drv, root, tail = self._parse_path(homedir)
        #     return self._from_parsed_parts(drv, root, tail + self._tail[1:])
        #
        # return self
        raise NotImplementedError
