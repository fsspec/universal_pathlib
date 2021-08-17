import sys
import pathlib
import warnings

import pytest

from upath import UPath
from upath.implementations.s3 import S3Path
from upath.tests.cases import BaseTests


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="don't run test on Windows",
)
def test_posix_path(local_testdir):
    assert isinstance(UPath(local_testdir), pathlib.PosixPath)


@pytest.mark.skipif(
    not sys.platform.startswith("win"),
    reason="only run test if Windows Machine",
)
def test_windows_path(local_testdir):
    assert isinstance(UPath(local_testdir), pathlib.WindowsPath)


def test_UPath_warning():
    with warnings.catch_warnings(record=True) as w:
        path = UPath("mock:/")  # noqa: F841
        assert len(w) == 1
        assert issubclass(w[-1].category, UserWarning)
        assert "mock" in str(w[-1].message)


class TestUpath(BaseTests):
    @pytest.fixture(autouse=True)
    def path(self, local_testdir):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.path = UPath(f"mock:{local_testdir}")

    def test_fsspec_compat(self):
        pass


@pytest.mark.hdfs
def test_multiple_backend_paths(local_testdir, s3, hdfs):
    anon, s3so = s3
    path = f"s3:{local_testdir}"
    s3_path = UPath(path, anon=anon, **s3so)
    assert s3_path.joinpath("text.txt")._url.scheme == "s3"
    host, user, port = hdfs
    path = f"hdfs:{local_testdir}"
    UPath(path, host=host, user=user, port=port)
    assert s3_path.joinpath("text1.txt")._url.scheme == "s3"


def test_constructor_accept_path(local_testdir):
    path = UPath(pathlib.Path(local_testdir))
    assert str(path) == str(pathlib.Path(local_testdir))


def test_constructor_accept_upath(local_testdir):
    path = UPath(UPath(local_testdir))
    assert str(path) == str(pathlib.Path(local_testdir))


def test_subclass(local_testdir):
    class MyPath(UPath):
        pass

    path = MyPath(local_testdir)
    assert str(path) == str(pathlib.Path(local_testdir))
    assert issubclass(MyPath, UPath)
    assert isinstance(path, pathlib.Path)


def test_instance_check(local_testdir):
    path = pathlib.Path(local_testdir)
    upath = UPath(local_testdir)
    # test instance check passes
    assert isinstance(upath, UPath)
    # test type is same as pathlib
    assert type(upath) is type(path)
    upath = UPath(f"file://{local_testdir}")
    # test default implementation is used
    assert type(upath) is UPath


def test_new_method(local_testdir):
    path = UPath.__new__(pathlib.Path, local_testdir)
    assert str(path) == str(pathlib.Path(local_testdir))
    assert isinstance(path, pathlib.Path)


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="don't run test on Windows",
)  # need to fix windows tests here
class TestFSSpecLocal(BaseTests):
    @pytest.fixture(autouse=True)
    def path(self, local_testdir):
        path = f"file://{local_testdir}"
        self.path = UPath(path)


PATHS = (
    ("path", "storage_options", "module", "object_type"),
    (
        ("/tmp/abc", (), None, pathlib.Path),
        ("s3://bucket/folder", ({"anon": True}), "s3fs", S3Path),
        ("gs://bucket/folder", ({"token": "anon"}), "gcsfs", UPath),
    ),
)


@pytest.mark.parametrize(*PATHS)
def test_create_from_type(path, storage_options, module, object_type):
    """Test that derived paths use same fs instance."""
    if module:
        # skip if module cannot be imported
        pytest.importorskip(module)
    try:
        upath = UPath(path, storage_options=storage_options)
        # test expected object type
        assert isinstance(upath, object_type)
        cast = type(upath)
        parent = upath.parent
        # test derived object is same type
        assert isinstance(parent, cast)
        # test that created fs uses fsspec instance cache
        assert not hasattr(upath, "fs") or upath.fs is parent.fs
        new = cast(str(parent))
        # test that object cast is same type
        assert isinstance(new, cast)
    except (ImportError, ModuleNotFoundError):
        # fs failed to import
        pass
