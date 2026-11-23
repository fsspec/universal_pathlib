import copy
import os
import pickle
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
    def test_rmdir_not_empty_warns_about_the_future_default(self):
        # wrapping a pathlib.Path, whose rmdir() already raises on a
        # non-empty directory: there is no future change to warn about
        p = self.path.joinpath("folder1")
        with pytest.raises(OSError):
            p.rmdir()
        assert p.exists()

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


def test_proxy_upath_copy_from_local(tmp_path):
    """Test ProxyUPath accepts extra kwargs in _copy_from()

    Regression test for https://github.com/fsspec/universal_pathlib/issues/546
    """

    class MyProxyPath(ProxyUPath):
        pass

    source = UPath(tmp_path / "test.txt")
    source.write_text("hello")

    destination = MyProxyPath("memory://bla/test_copy_from.txt")
    source.move(destination)

    assert destination.read_text() == "hello"


class MemoryAndLocalUPath(ProxyUPath):
    # "file" allows the cross filesystem copy/move tests to local targets
    supported_protocols = ("memory", "file")


class MemoryOnlyUPath(ProxyUPath, supported_protocols=("memory",)):
    pass


class TestRestrictedProxyMemoryPath(BaseTests, metaclass=OverrideMeta):
    @pytest.fixture(autouse=True)
    def path(self, local_testdir):
        if not local_testdir.startswith("/"):
            local_testdir = "/" + local_testdir
        self.path = MemoryAndLocalUPath(f"memory:{local_testdir}")
        self.prepare_file_system()

    @overrides_base
    def test_is_correct_class(self):
        assert isinstance(self.path, MemoryAndLocalUPath)


def test_supported_protocols_default():
    assert ProxyUPath.supported_protocols is None

    class MyProxyPath(ProxyUPath):
        pass

    assert MyProxyPath.supported_protocols is None
    assert MyProxyPath("memory:///a").protocol == "memory"
    assert MyProxyPath("s3://bucket/a").protocol == "s3"


def _restricted_via_attribute(protocols):
    class MyProxyPath(ProxyUPath):
        supported_protocols = protocols

    return MyProxyPath


def _restricted_via_keyword(protocols):
    class MyProxyPath(ProxyUPath, supported_protocols=protocols):
        pass

    return MyProxyPath


@pytest.fixture(params=[_restricted_via_attribute, _restricted_via_keyword])
def make_restricted_cls(request):
    return request.param


@pytest.mark.parametrize(
    "supported,uri",
    [
        (("memory",), "memory:///a/b"),
        (("s3",), "s3://bucket/a"),
        # fsspec protocol aliases
        (("s3",), "s3a://bucket/a"),
        (("s3a",), "s3://bucket/a"),
        (("gcs",), "gs://bucket/a"),
        (("gs",), "gcs://bucket/a"),
        (("az",), "abfs://container/a"),
        (("az",), "abfss://container/a"),
        # local paths
        (("file",), "file:///tmp/a"),
        (("file",), "local:///tmp/a"),
        (("file",), "/tmp/a"),
        (("local",), "file:///tmp/a"),
        (("",), "file:///tmp/a"),
        (("",), "/tmp/a"),
        # protocols unknown to fsspec only match exactly
        (("unknown-proto", "memory"), "memory:///a"),
    ],
)
def test_supported_protocols(make_restricted_cls, supported, uri):
    cls = make_restricted_cls(supported)
    assert cls.supported_protocols == supported
    p = cls(uri)
    assert isinstance(p, cls)


@pytest.mark.parametrize(
    "supported,uri",
    [
        (("s3",), "memory:///a/b"),
        (("s3", "gcs"), "az://container/a"),
        (("az",), "adl://store/a"),
        (("memory",), "file:///tmp/a"),
        (("memory",), "/tmp/a"),
        (("file",), "memory:///a"),
        (("s3",), "simplecache::s3://bucket/a"),
        (("unknown-proto",), "memory:///a"),
    ],
)
def test_supported_protocols_incompatible(make_restricted_cls, supported, uri):
    cls = make_restricted_cls(supported)
    # raises TypeError, but stays backwards compatible with ValueError
    with pytest.raises(TypeError, match=r"incompatible with MyProxyPath") as e:
        cls(uri)
    assert isinstance(e.value, ValueError)
    assert repr(supported) in str(e.value)


def test_supported_protocols_incompatible_protocol_kwarg():
    class MyProxyPath(ProxyUPath, supported_protocols=("s3",)):
        pass

    with pytest.raises(TypeError, match="incompatible with MyProxyPath"):
        MyProxyPath("bucket/a", protocol="memory")
    with pytest.raises(TypeError, match="incompatible with MyProxyPath"):
        MyProxyPath.from_uri("memory:///a")


def test_supported_protocols_inherited():
    class MyProxyPath(ProxyUPath, supported_protocols=("memory",)):
        pass

    class MySubProxyPath(MyProxyPath):
        pass

    class MyOtherSubProxyPath(MyProxyPath):
        supported_protocols = ("s3",)

    assert MySubProxyPath.supported_protocols == ("memory",)
    assert isinstance(MySubProxyPath("memory:///a"), MySubProxyPath)
    with pytest.raises(TypeError, match="incompatible with MySubProxyPath"):
        MySubProxyPath("s3://bucket/a")

    assert isinstance(MyOtherSubProxyPath("s3://bucket/a"), MyOtherSubProxyPath)
    with pytest.raises(TypeError, match="incompatible with MyOtherSubProxyPath"):
        MyOtherSubProxyPath("memory:///a")


def test_supported_protocols_normalized_to_tuple():
    class MyProxyPath(ProxyUPath):
        supported_protocols = ["memory", "s3"]  # type: ignore[assignment]

    assert MyProxyPath.supported_protocols == ("memory", "s3")


@pytest.mark.parametrize("protocols", ["memory", ("memory", 1), 1])
def test_supported_protocols_invalid(make_restricted_cls, protocols):
    with pytest.raises(TypeError, match="must be a tuple of protocol strings"):
        make_restricted_cls(protocols)


def test_supported_protocols_keyword_and_attribute():
    with pytest.raises(TypeError, match="not both"):

        class MyProxyPath(ProxyUPath, supported_protocols=("s3",)):
            supported_protocols = ("memory",)


@pytest.mark.usefixtures("clear_fsspec_memory_cache")
def test_supported_protocols_derived_paths():
    base = MemoryOnlyUPath("memory:///base")
    base.joinpath("dir").mkdir(parents=True)
    file = base / "dir" / "file.txt"
    file.write_text("hello")

    derived = [
        base.joinpath("dir"),
        file.parent,
        *file.parents,
        file.with_name("other.txt"),
        file.with_suffix(".csv"),
        file.with_stem("other"),
        file.absolute(),
        file.resolve(),
        file.relative_to(base),
        *base.iterdir(),
        *base.glob("**/*.txt"),
        *base.rglob("*.txt"),
        *(p for p, _, _ in base.walk()),
        pickle.loads(pickle.dumps(file)),
        copy.copy(file),
        copy.deepcopy(file),
        file.copy("memory:///base/dir/copied.txt"),
        file.copy(UPath("memory:///base/dir/copied2.txt")),
        file.copy_into(MemoryOnlyUPath("memory:///base")),
        base.joinpath("dir", "copied.txt").move("memory:///base/moved.txt"),
        base.joinpath("dir", "copied2.txt").move_into("memory:///base"),
    ]
    for p in derived:
        assert isinstance(p, MemoryOnlyUPath)
        assert p.protocol == "memory"


@pytest.mark.usefixtures("clear_fsspec_memory_cache")
def test_supported_protocols_cross_filesystem_operations(tmp_path):
    class MyProxyPath(ProxyUPath, supported_protocols=("memory",)):
        pass

    file = MyProxyPath("memory:///base/file.txt")
    file.write_text("hello")
    target = tmp_path.joinpath("target.txt")

    # the returned path would have an unsupported protocol
    with pytest.raises(TypeError, match="incompatible with MyProxyPath"):
        file.joinuri("s3://bucket/a")

    # check before modifying any filesystem
    for target_arg in [str(target), target, UPath(target)]:
        with pytest.raises(TypeError, match="incompatible with MyProxyPath"):
            file.copy(target_arg)
        with pytest.raises(TypeError, match="incompatible with MyProxyPath"):
            file.move(target_arg)
    for target_dir_arg in [str(tmp_path), tmp_path, UPath(tmp_path)]:
        with pytest.raises(TypeError, match="incompatible with MyProxyPath"):
            file.copy_into(target_dir_arg)
    # note: str target dirs are interpreted relative to the source filesystem
    for target_dir_arg in [tmp_path, UPath(tmp_path)]:
        with pytest.raises(TypeError, match="incompatible with MyProxyPath"):
            file.move_into(target_dir_arg)
    assert not target.exists()
    assert list(tmp_path.iterdir()) == []
    assert file.read_text() == "hello"


def test_supported_protocols_local_copy_and_move(tmp_path):
    class LocalProxyPath(ProxyUPath, supported_protocols=("file",)):
        pass

    source = LocalProxyPath(tmp_path / "source.txt")
    source.write_text("hello")
    tmp_path.joinpath("folder").mkdir()

    copied = source.copy_into(tmp_path / "folder")
    assert isinstance(copied, LocalProxyPath)
    assert copied.read_text() == "hello"

    moved = copied.move(tmp_path / "moved.txt")
    assert isinstance(moved, LocalProxyPath)
    assert moved.read_text() == "hello"
