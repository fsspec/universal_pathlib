import sys
import pathlib
import warnings
from pathlib import Path

import pytest

from upath import UPath
from upath.tests.cases import BaseTests


@pytest.mark.skipif(
    sys.platform != "linux", reason="only run test if Linux Machine"
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
    assert str(path) == str(Path(local_testdir))


def test_constructor_accept_upath(local_testdir):
    path = UPath(UPath(local_testdir))
    assert str(path) == str(Path(local_testdir))


def test_subclass(local_testdir):
    class MyPath(UPath):
        pass

    path = MyPath(local_testdir)
    assert str(path) == str(Path(local_testdir))
    assert issubclass(MyPath, UPath)
    assert isinstance(path, pathlib.Path)


def test_instance_check(local_testdir):
    path = UPath(local_testdir)
    assert isinstance(path, UPath)


def test_new_method(local_testdir):
    path = UPath.__new__(pathlib.Path, local_testdir)
    assert str(path) == str(Path(local_testdir))
    assert isinstance(path, pathlib.Path)
