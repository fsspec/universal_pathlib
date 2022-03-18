import pathlib
import pickle
import sys
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

            # On Windows the path needs to be prefixed with `/`, becaue
            # `UPath` implements `_posix_flavour`, which requires a `/` root
            # in order to correctly deserialize pickled objects
            root = "/" if sys.platform.startswith("win") else ""
            self.path = UPath(f"mock:{root}{local_testdir}")

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


def test_child_path():
    path_a = UPath("gcs://bucket/folder")
    path_b = UPath("gcs://bucket") / "folder"

    assert str(path_a) == str(path_b)
    assert path_a._root == path_b._root
    assert path_a._drv == path_b._drv
    assert path_a._parts == path_b._parts
    assert path_a._url == path_b._url


def test_pickling():
    path = UPath("gcs://bucket/folder", storage_options={"anon": True})
    pickled_path = pickle.dumps(path)
    recovered_path = pickle.loads(pickled_path)

    assert type(path) == type(recovered_path)
    assert str(path) == str(recovered_path)
    assert path.fs.storage_options == recovered_path.fs.storage_options


def test_pickling_child_path():
    path = UPath("gcs://bucket", anon=True) / "subfolder" / "subsubfolder"
    pickled_path = pickle.dumps(path)
    recovered_path = pickle.loads(pickled_path)

    assert type(path) == type(recovered_path)
    assert str(path) == str(recovered_path)
    assert path._drv == recovered_path._drv
    assert path._root == recovered_path._root
    assert path._parts == recovered_path._parts
    assert path.fs.storage_options == recovered_path.fs.storage_options
