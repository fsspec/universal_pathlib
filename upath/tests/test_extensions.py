import os
import sys
from contextlib import nullcontext

import pytest

from upath import UnsupportedOperation
from upath import UPath
from upath.extensions import ProxyUPath
from upath.implementations.local import FilePath
from upath.implementations.local import PosixUPath
from upath.implementations.local import WindowsUPath
from upath.implementations.memory import MemoryPath

from .cases import BaseTests
from .utils import OverrideMeta
from .utils import extends_base
from .utils import overrides_base


class TestProxyMemoryPath(BaseTests, metaclass=OverrideMeta):
    @pytest.fixture(autouse=True)
    def path(self, local_testdir):
        if not local_testdir.startswith("/"):
            local_testdir = "/" + local_testdir
        self.path = ProxyUPath(f"memory:{local_testdir}")
        self.prepare_file_system()

    @overrides_base
    def test_is_correct_class(self):
        assert isinstance(self.path, ProxyUPath)

    @extends_base
    def test_is_not_wrapped_class(self):
        assert not isinstance(self.path, MemoryPath)


class TestProxyFilePath(BaseTests, metaclass=OverrideMeta):
    @pytest.fixture(autouse=True)
    def path(self, local_testdir):
        self.path = ProxyUPath(f"file://{local_testdir}")
        self.prepare_file_system()

    @overrides_base
    def test_is_correct_class(self):
        assert isinstance(self.path, ProxyUPath)

    @extends_base
    def test_is_not_wrapped_class(self):
        assert not isinstance(self.path, FilePath)

    @overrides_base
    def test_chmod(self):
        self.path.joinpath("file1.txt").chmod(777)

    @overrides_base
    def test_cwd(self):
        # ProxyUPath.cwd() works differently on the instance
        self.path.cwd()
        with pytest.raises(UnsupportedOperation):
            type(self.path).cwd()


class TestProxyPathlibPath(BaseTests, metaclass=OverrideMeta):
    @pytest.fixture(autouse=True)
    def path(self, local_testdir):
        self.path = ProxyUPath(f"{local_testdir}")
        self.prepare_file_system()

    @overrides_base
    def test_is_correct_class(self):
        assert isinstance(self.path, ProxyUPath)

    @extends_base
    def test_is_not_wrapped_class(self):
        assert not isinstance(self.path, (PosixUPath, WindowsUPath))

    @overrides_base
    def test_chmod(self):
        self.path.joinpath("file1.txt").chmod(777)

    @overrides_base
    @pytest.mark.skipif(
        sys.version_info < (3, 12), reason="storage options only handled in 3.12+"
    )
    def test_eq(self):
        super().test_eq()

    if sys.version_info < (3, 12):

        @overrides_base
        def test_storage_options_dont_affect_hash(self):
            # On Python < 3.12, storage_options trigger warnings for LocalPath
            with pytest.warns(
                UserWarning,
                match=r".*on python <= \(3, 11\) ignores protocol and storage_options",
            ):
                super().test_storage_options_dont_affect_hash()

    @overrides_base
    def test_group(self):
        pytest.importorskip("grp")
        self.path.group()

    @overrides_base
    def test_owner(self):
        pytest.importorskip("pwd")
        self.path.owner()

    @overrides_base
    def test_readlink(self):
        try:
            os.readlink
        except AttributeError:
            pytest.skip("os.readlink not available on this platform")
        with pytest.raises((OSError, UnsupportedOperation)):
            self.path.readlink()

    @overrides_base
    def test_protocol(self):
        assert self.path.protocol == ""

    @overrides_base
    def test_as_uri(self):
        assert self.path.as_uri().startswith("file://")

    if sys.version_info < (3, 10):

        @overrides_base
        def test_lstat(self):
            # On Python < 3.10, stat(follow_symlinks=False) triggers warnings
            with pytest.warns(
                UserWarning,
                match=r".*stat\(\) follow_symlinks=False is currently ignored",
            ):
                st = self.path.lstat()
            assert st is not None

    else:

        @overrides_base
        def test_lstat(self):
            st = self.path.lstat()
            assert st is not None

    @overrides_base
    def test_relative_to(self):
        base = self.path
        child = self.path / "folder1" / "file1.txt"
        relative = child.relative_to(base)
        assert str(relative) == f"folder1{os.sep}file1.txt"

    @overrides_base
    def test_cwd(self):
        self.path.cwd()
        with pytest.raises(UnsupportedOperation):
            type(self.path).cwd()

    @overrides_base
    def test_lchmod(self):
        # setup
        a = self.path.joinpath("a")
        b = self.path.joinpath("b")
        a.touch()
        b.symlink_to(a)

        # see: https://github.com/python/cpython/issues/108660#issuecomment-1854645898
        if hasattr(os, "lchmod") or os.chmod in os.supports_follow_symlinks:
            cm = nullcontext()
        else:
            cm = pytest.raises((UnsupportedOperation, NotImplementedError))
        with cm:
            b.lchmod(mode=0o777)

    @overrides_base
    def test_symlink_to(self):
        self.path.joinpath("link").symlink_to(self.path)

    @overrides_base
    def test_hardlink_to(self):
        try:
            self.path.joinpath("link").hardlink_to(self.path)
        except PermissionError:
            pass  # hardlink may require elevated permissions


def test_custom_subclass():

    class ReversePath(ProxyUPath):
        def read_bytes_reversed(self):
            return self.read_bytes()[::-1]

        def write_bytes_reversed(self, value):
            self.write_bytes(value[::-1])

    b = MemoryPath("memory://base")

    p = b.joinpath("file1")
    p.write_bytes(b"dlrow olleh")

    r = ReversePath("memory://base/file1")
    assert r.read_bytes_reversed() == b"hello world"

    r.parent.joinpath("file2").write_bytes_reversed(b"dlrow olleh")
    assert b.joinpath("file2").read_bytes() == b"hello world"


def test_protocol_dispatch_deprecation_warning():

    class MyPath(UPath):
        _protocol_dispatch = False

    with pytest.warns(DeprecationWarning, match="_protocol_dispatch = False"):
        a = MyPath(".", protocol="memory")

    assert isinstance(a, MyPath)


# Protocol to sample URI mapping for compatibility tests
_PROTOCOL_URIS = {
    "s3": "s3://bucket/folder",
    "gs": "gs://bucket/folder",
    "memory": "memory://folder",
    "file": "file:/tmp/folder",
    "http": "http://example.com/path",
    "": "/tmp/folder",
}

# Generate incompatible combinations
_PROXY_INCOMPATIBLE_CASES = [
    (_PROTOCOL_URIS[uri_protocol], target_protocol)
    for target_protocol in _PROTOCOL_URIS
    for uri_protocol in _PROTOCOL_URIS
    if target_protocol != uri_protocol and uri_protocol != ""
]


@pytest.mark.parametrize("uri,protocol", _PROXY_INCOMPATIBLE_CASES)
def test_proxy_subclass_incompatible_protocol_uri(uri, protocol):
    """Test that ProxyUPath subclasses raise TypeError for incompatible protocols."""

    class MyProxyPath(ProxyUPath):
        pass

    # ProxyUPath wraps the underlying path, so it should also raise TypeError
    with pytest.raises(TypeError, match=r".*incompatible with"):
        MyProxyPath(uri, protocol=protocol)
