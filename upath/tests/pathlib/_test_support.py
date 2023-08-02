"""vendoring everything needed to run test_pathlib.py

https://github.com/python/cpython/tree/10bf2cd404320252ef162d5699cb7ce52a970d44

from test.support import import_helper
from test.support import set_recursion_limit
from test.support import is_emscripten, is_wasi
from test.support import os_helper
from test.support.os_helper import TESTFN, FakePath
"""
import os
import stat
import string
import sys
import collections.abc
import contextlib
import time
import warnings
from types import SimpleNamespace

import pytest
from pytest import importorskip

import_helper = SimpleNamespace(import_module=importorskip)
import_module = importorskip


@contextlib.contextmanager
def set_recursion_limit(limit):
    """Temporarily change the recursion limit."""
    original_limit = sys.getrecursionlimit()
    try:
        sys.setrecursionlimit(limit)
        yield
    finally:
        sys.setrecursionlimit(original_limit)


is_emscripten = sys.platform == "emscripten"
is_wasi = sys.platform == "wasi"


class FakePath:
    """Simple implementation of the path protocol."""

    def __init__(self, path):
        self.path = path

    def __repr__(self):
        return f"<FakePath {self.path!r}>"

    def __fspath__(self):
        if (
            isinstance(self.path, BaseException)
            or isinstance(self.path, type)
            and issubclass(self.path, BaseException)
        ):
            raise self.path
        else:
            return self.path


class EnvironmentVarGuard(collections.abc.MutableMapping):

    """Class to help protect the environment variable properly.  Can be used as
    a context manager."""

    def __init__(self):
        self._environ = os.environ
        self._changed = {}

    def __getitem__(self, envvar):
        return self._environ[envvar]

    def __setitem__(self, envvar, value):
        # Remember the initial value on the first access
        if envvar not in self._changed:
            self._changed[envvar] = self._environ.get(envvar)
        self._environ[envvar] = value

    def __delitem__(self, envvar):
        # Remember the initial value on the first access
        if envvar not in self._changed:
            self._changed[envvar] = self._environ.get(envvar)
        if envvar in self._environ:
            del self._environ[envvar]

    def keys(self):
        return self._environ.keys()

    def __iter__(self):
        return iter(self._environ)

    def __len__(self):
        return len(self._environ)

    def set(self, envvar, value):
        self[envvar] = value

    def unset(self, envvar):
        del self[envvar]

    def copy(self):
        # We do what os.environ.copy() does.
        return dict(self)

    def __enter__(self):
        return self

    def __exit__(self, *ignore_exc):
        for k, v in self._changed.items():
            if v is None:
                if k in self._environ:
                    del self._environ[k]
            else:
                self._environ[k] = v
        os.environ = self._environ


# Filename used for testing
TESTFN_ASCII = "@test"

# Disambiguate TESTFN for parallel testing, while letting it remain a valid
# module name.
TESTFN_ASCII = "{}_{}_tmp".format(TESTFN_ASCII, os.getpid())


# FS_NONASCII: non-ASCII character encodable by os.fsencode(),
# or an empty string if there is no such character.
FS_NONASCII = ""
for character in (
    # First try printable and common characters to have a readable filename.
    # For each character, the encoding list are just example of encodings able
    # to encode the character (the list is not exhaustive).
    # U+00E6 (Latin Small Letter Ae): cp1252, iso-8859-1
    "\u00E6",
    # U+0130 (Latin Capital Letter I With Dot Above): cp1254, iso8859_3
    "\u0130",
    # U+0141 (Latin Capital Letter L With Stroke): cp1250, cp1257
    "\u0141",
    # U+03C6 (Greek Small Letter Phi): cp1253
    "\u03C6",
    # U+041A (Cyrillic Capital Letter Ka): cp1251
    "\u041A",
    # U+05D0 (Hebrew Letter Alef): Encodable to cp424
    "\u05D0",
    # U+060C (Arabic Comma): cp864, cp1006, iso8859_6, mac_arabic
    "\u060C",
    # U+062A (Arabic Letter Teh): cp720
    "\u062A",
    # U+0E01 (Thai Character Ko Kai): cp874
    "\u0E01",
    # Then try more "special" characters. "special" because they may be
    # interpreted or displayed differently depending on the exact locale
    # encoding and the font.
    # U+00A0 (No-Break Space)
    "\u00A0",
    # U+20AC (Euro Sign)
    "\u20AC",
):
    try:
        # If Python is set up to use the legacy 'mbcs' in Windows,
        # 'replace' error mode is used, and encode() returns b'?'
        # for characters missing in the ANSI codepage
        if os.fsdecode(os.fsencode(character)) != character:
            raise UnicodeError
    except UnicodeError:
        pass
    else:
        FS_NONASCII = character
        break


# TESTFN_UNDECODABLE is a filename (bytes type) that should *not* be able to be
# decoded from the filesystem encoding (in strict mode). It can be None if we
# cannot generate such filename (ex: the latin1 encoding can decode any byte
# sequence). On UNIX, TESTFN_UNDECODABLE can be decoded by os.fsdecode() thanks
# to the surrogateescape error handler (PEP 383), but not from the filesystem
# encoding in strict mode.
TESTFN_UNDECODABLE = None
for name in (
    # b'\xff' is not decodable by os.fsdecode() with code page 932. Windows
    # accepts it to create a file or a directory, or don't accept to enter to
    # such directory (when the bytes name is used). So test b'\xe7' first:
    # it is not decodable from cp932.
    b"\xe7w\xf0",
    # undecodable from ASCII, UTF-8
    b"\xff",
    # undecodable from iso8859-3, iso8859-6, iso8859-7, cp424, iso8859-8, cp856
    # and cp857
    b"\xae\xd5"
    # undecodable from UTF-8 (UNIX and Mac OS X)
    b"\xed\xb2\x80",
    b"\xed\xb4\x80",
    # undecodable from shift_jis, cp869, cp874, cp932, cp1250, cp1251, cp1252,
    # cp1253, cp1254, cp1255, cp1257, cp1258
    b"\x81\x98",
):
    try:
        name.decode(sys.getfilesystemencoding())
    except UnicodeDecodeError:
        try:
            name.decode(
                sys.getfilesystemencoding(), sys.getfilesystemencodeerrors()
            )
        except UnicodeDecodeError:
            continue
        TESTFN_UNDECODABLE = os.fsencode(TESTFN_ASCII) + name
        break

if FS_NONASCII:
    TESTFN_NONASCII = TESTFN_ASCII + FS_NONASCII
else:
    TESTFN_NONASCII = None
TESTFN = TESTFN_NONASCII or TESTFN_ASCII


_can_symlink = None


def can_symlink():
    global _can_symlink
    if _can_symlink is not None:
        return _can_symlink
    # WASI / wasmtime prevents symlinks with absolute paths, see man
    # openat2(2) RESOLVE_BENEATH. Almost all symlink tests use absolute
    # paths. Skip symlink tests on WASI for now.
    src = os.path.abspath(TESTFN)
    symlink_path = src + "can_symlink"
    try:
        os.symlink(src, symlink_path)
        can = True
    except (OSError, NotImplementedError, AttributeError):
        can = False
    else:
        os.remove(symlink_path)
    _can_symlink = can
    return can


def skip_unless_symlink(test):
    """Skip decorator for tests that require functional symlink"""
    ok = can_symlink()
    msg = "Requires functional symlink implementation"
    return test if ok else pytest.mark.skip(msg)(test)


_can_chmod = None


def can_chmod():
    global _can_chmod
    if _can_chmod is not None:
        return _can_chmod
    if not hasattr(os, "chown"):
        _can_chmod = False
        return _can_chmod
    try:
        with open(TESTFN, "wb") as _:
            try:
                os.chmod(TESTFN, 0o777)
                mode1 = os.stat(TESTFN).st_mode
                os.chmod(TESTFN, 0o666)
                mode2 = os.stat(TESTFN).st_mode
            except OSError:
                can = False
            else:
                can = stat.S_IMODE(mode1) != stat.S_IMODE(mode2)
    finally:
        unlink(TESTFN)
    _can_chmod = can
    return can


def skip_unless_working_chmod(test):
    """Skip tests that require working os.chmod()

    WASI SDK 15.0 cannot change file mode bits.
    """
    ok = can_chmod()
    msg = "requires working os.chmod()"
    return test if ok else pytest.mark.skip(msg)(test)


def unlink(filename):
    try:
        _unlink(filename)
    except (FileNotFoundError, NotADirectoryError):
        pass


if sys.platform.startswith("win"):
    def _waitfor(func, pathname, waitall=False):
        # Perform the operation
        func(pathname)
        # Now setup the wait loop
        if waitall:
            dirname = pathname
        else:
            dirname, name = os.path.split(pathname)
            dirname = dirname or '.'
        # Check for `pathname` to be removed from the filesystem.
        # The exponential backoff of the timeout amounts to a total
        # of ~1 second after which the deletion is probably an error
        # anyway.
        # Testing on an i7@4.3GHz shows that usually only 1 iteration is
        # required when contention occurs.
        timeout = 0.001
        while timeout < 1.0:
            # Note we are only testing for the existence of the file(s) in
            # the contents of the directory regardless of any security or
            # access rights.  If we have made it this far, we have sufficient
            # permissions to do that much using Python's equivalent of the
            # Windows API FindFirstFile.
            # Other Windows APIs can fail or give incorrect results when
            # dealing with files that are pending deletion.
            L = os.listdir(dirname)
            if not (L if waitall else name in L):
                return
            # Increase the timeout and try again
            time.sleep(timeout)
            timeout *= 2
        warnings.warn('tests may fail, delete still pending for ' + pathname,
                      RuntimeWarning, stacklevel=4)

    def _unlink(filename):
        _waitfor(os.unlink, filename)

    def _rmdir(dirname):
        _waitfor(os.rmdir, dirname)

    def _rmtree(path):
        from test.support import _force_run

        def _rmtree_inner(path):
            for name in _force_run(path, os.listdir, path):
                fullname = os.path.join(path, name)
                try:
                    mode = os.lstat(fullname).st_mode
                except OSError as exc:
                    print("support.rmtree(): os.lstat(%r) failed with %s"
                          % (fullname, exc),
                          file=sys.__stderr__)
                    mode = 0
                if stat.S_ISDIR(mode):
                    _waitfor(_rmtree_inner, fullname, waitall=True)
                    _force_run(fullname, os.rmdir, fullname)
                else:
                    _force_run(fullname, os.unlink, fullname)
        _waitfor(_rmtree_inner, path, waitall=True)
        _waitfor(lambda p: _force_run(p, os.rmdir, p), path)

    def _longpath(path):
        try:
            import ctypes
        except ImportError:
            # No ctypes means we can't expands paths.
            pass
        else:
            buffer = ctypes.create_unicode_buffer(len(path) * 2)
            length = ctypes.windll.kernel32.GetLongPathNameW(path, buffer,
                                                             len(buffer))
            if length:
                return buffer[:length]
        return path
else:
    _unlink = os.unlink
    _rmdir = os.rmdir

    def _rmtree(path):
        import shutil
        try:
            shutil.rmtree(path)
            return
        except OSError:
            pass

        def _rmtree_inner(path):
            from test.support import _force_run
            for name in _force_run(path, os.listdir, path):
                fullname = os.path.join(path, name)
                try:
                    mode = os.lstat(fullname).st_mode
                except OSError:
                    mode = 0
                if stat.S_ISDIR(mode):
                    _rmtree_inner(fullname)
                    _force_run(path, os.rmdir, fullname)
                else:
                    _force_run(path, os.unlink, fullname)
        _rmtree_inner(path)
        os.rmdir(path)

    def _longpath(path):
        return path


def rmdir(dirname):
    try:
        _rmdir(dirname)
    except FileNotFoundError:
        pass


def rmtree(path):
    try:
        _rmtree(path)
    except FileNotFoundError:
        pass


def fs_is_case_insensitive(directory):
    """Detects if the file system for the specified directory
    is case-insensitive."""
    import tempfile

    with tempfile.NamedTemporaryFile(dir=directory) as base:
        base_path = base.name
        case_path = base_path.upper()
        if case_path == base_path:
            case_path = base_path.lower()
        try:
            return os.path.samefile(base_path, case_path)
        except FileNotFoundError:
            return False


@contextlib.contextmanager
def change_cwd(path, quiet=False):
    """Return a context manager that changes the current working directory.

    Arguments:

      path: the directory to use as the temporary current working directory.

      quiet: if False (the default), the context manager raises an exception
        on error.  Otherwise, it issues only a warning and keeps the current
        working directory the same.

    """
    saved_dir = os.getcwd()
    try:
        os.chdir(os.path.realpath(path))
    except OSError as exc:
        if not quiet:
            raise
        warnings.warn(
            f"tests may fail, unable to change the current working "
            f"directory to {path!r}: {exc}",
            RuntimeWarning,
            stacklevel=3,
        )
    try:
        yield os.getcwd()
    finally:
        os.chdir(saved_dir)


try:
    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    ERROR_FILE_NOT_FOUND = 2
    DDD_REMOVE_DEFINITION = 2
    DDD_EXACT_MATCH_ON_REMOVE = 4
    DDD_NO_BROADCAST_SYSTEM = 8
except (ImportError, AttributeError):

    @contextlib.contextmanager
    def subst_drive(path):
        raise pytest.skip("ctypes or kernel32 is not available")

else:

    @contextlib.contextmanager
    def subst_drive(path):
        """Temporarily yield a substitute drive for a given path."""
        for c in reversed(string.ascii_uppercase):
            drive = f"{c}:"
            if (
                not kernel32.QueryDosDeviceW(drive, None, 0)
                and ctypes.get_last_error() == ERROR_FILE_NOT_FOUND
            ):
                break
        else:
            raise pytest.skip("no available logical drive")
        if not kernel32.DefineDosDeviceW(DDD_NO_BROADCAST_SYSTEM, drive, path):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            yield drive
        finally:
            if not kernel32.DefineDosDeviceW(
                DDD_REMOVE_DEFINITION | DDD_EXACT_MATCH_ON_REMOVE, drive, path
            ):
                raise ctypes.WinError(ctypes.get_last_error())


os_helper = SimpleNamespace(
    rmtree=rmtree,
    can_symlink=can_symlink,
    skip_unless_symlink=skip_unless_symlink,
    TESTFN=TESTFN,
    _longpath=_longpath,
    EnvironmentVarGuard=EnvironmentVarGuard,
    skip_unless_working_chmod=skip_unless_working_chmod,
    fs_is_case_insensitive=fs_is_case_insensitive,
    change_cwd=change_cwd,
    subst_drive=subst_drive,
)
