import os
import pathlib
import pickle
import sys
import warnings
from typing import Mapping
from urllib.parse import SplitResult

import pytest

from upath import UPath
from upath.implementations.cloud import GCSPath
from upath.implementations.cloud import S3Path

from .cases import BaseTests
from .utils import only_on_windows
from .utils import skip_on_windows
from .utils import xfail_if_version


@skip_on_windows
def test_posix_path(local_testdir):
    assert isinstance(UPath(local_testdir), pathlib.PosixPath)


@only_on_windows
def test_windows_path(local_testdir):
    assert isinstance(UPath(local_testdir), pathlib.WindowsPath)


def test_UPath_untested_protocol_warning(clear_registry):
    with warnings.catch_warnings(record=True) as w:
        _ = UPath("mock:/")
        assert len(w) == 1
        assert issubclass(w[-1].category, UserWarning)
        assert "mock" in str(w[-1].message)


def test_UPath_file_protocol_no_warning():
    with warnings.catch_warnings(record=True) as w:
        _ = UPath("file:/")
        assert len(w) == 0


class TestUpath(BaseTests):
    @pytest.fixture(autouse=True)
    def path(self, local_testdir):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            # On Windows the path needs to be prefixed with `/`, because
            # `UPath` implements `_posix_flavour`, which requires a `/` root
            # in order to correctly deserialize pickled objects
            root = "/" if sys.platform.startswith("win") else ""
            self.path = UPath(f"mock:{root}{local_testdir}")

    def test_fsspec_compat(self):
        pass

    def test_cwd(self):
        pth = type(self.path).cwd()
        assert str(pth) == os.getcwd()
        assert isinstance(pth, pathlib.Path)
        assert isinstance(pth, UPath)

    def test_home(self):
        pth = type(self.path).home()
        assert str(pth) == os.path.expanduser("~")
        assert isinstance(pth, pathlib.Path)
        assert isinstance(pth, UPath)

    @xfail_if_version("fsspec", reason="", ge="2024.2.0")
    def test_iterdir_no_dir(self):
        # the mock filesystem is basically just LocalFileSystem,
        # so this test would need to have an iterdir fix.
        super().test_iterdir_no_dir()


def test_multiple_backend_paths(local_testdir):
    path = "s3://bucket/"
    s3_path = UPath(path, anon=True)
    assert s3_path.joinpath("text.txt")._url.scheme == "s3"
    path = f"file://{local_testdir}"
    UPath(path)
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

    with pytest.warns(
        DeprecationWarning, match=r"MyPath\(...\) detected protocol '' .*"
    ):
        path = MyPath(local_testdir)
    assert str(path) == str(pathlib.Path(local_testdir))
    assert issubclass(MyPath, UPath)
    assert isinstance(path, pathlib.Path)


def test_subclass_with_gcs():
    path = UPath("gcs://bucket", anon=True)
    assert isinstance(path, UPath)
    assert isinstance(path, pathlib.Path)


def test_instance_check(local_testdir):
    upath = UPath(local_testdir)
    # test instance check passes
    assert isinstance(upath, pathlib.Path)
    assert isinstance(upath, UPath)


def test_instance_check_local_uri(local_testdir):
    upath = UPath(f"file://{local_testdir}")
    assert isinstance(upath, pathlib.Path)
    assert isinstance(upath, UPath)


@pytest.mark.xfail(reason="unsupported on universal_pathlib>0.1.4")
def test_new_method(local_testdir):
    path = UPath.__new__(pathlib.Path, local_testdir)
    assert str(path) == str(pathlib.Path(local_testdir))
    assert isinstance(path, pathlib.Path)
    assert isinstance(path, UPath)


PATHS = (
    ("path", "storage_options", "module", "object_type"),
    (
        ("/tmp/abc", {}, None, pathlib.Path),
        ("s3://bucket/folder", {"anon": True}, "s3fs", S3Path),
        ("gs://bucket/folder", {"token": "anon"}, "gcsfs", GCSPath),
    ),
)


@pytest.mark.parametrize(*PATHS)
def test_create_from_type(path, storage_options, module, object_type):
    """Test that derived paths use same fs instance."""
    if module:
        # skip if module cannot be imported
        pytest.importorskip(module)
    upath = UPath(path, **storage_options)
    # test expected object type
    assert isinstance(upath, object_type)
    cast = type(upath)
    parent = upath.parent
    # test derived object is same type
    assert isinstance(parent, cast)
    # test that created fs uses fsspec instance cache
    assert upath.fs is parent.fs
    new = cast(str(parent), **storage_options)
    # test that object cast is same type
    assert isinstance(new, cast)


def test_list_args():
    path_a = UPath("gcs://bucket", "folder")
    path_b = UPath("gcs://bucket") / "folder"

    assert str(path_a) == str(path_b)
    assert path_a.root == path_b.root
    assert path_a.drive == path_b.drive
    assert path_a.parts == path_b.parts
    assert path_a._url == path_b._url


def test_child_path():
    path_a = UPath("gcs://bucket/folder")
    path_b = UPath("gcs://bucket") / "folder"

    assert str(path_a) == str(path_b)
    assert path_a.root == path_b.root
    assert path_a.drive == path_b.drive
    assert path_a.parts == path_b.parts
    assert path_a._url == path_b._url


def test_pickling():
    path = UPath("gcs://bucket/folder", token="anon")
    pickled_path = pickle.dumps(path)
    recovered_path = pickle.loads(pickled_path)

    assert type(path) is type(recovered_path)
    assert str(path) == str(recovered_path)
    assert path.storage_options == recovered_path.storage_options


def test_pickling_child_path():
    path = UPath("gcs://bucket", token="anon") / "subfolder" / "subsubfolder"
    pickled_path = pickle.dumps(path)
    recovered_path = pickle.loads(pickled_path)

    assert type(path) is type(recovered_path)
    assert str(path) == str(recovered_path)
    assert path.drive == recovered_path.drive
    assert path.root == recovered_path.root
    assert path.parts == recovered_path.parts
    assert path.storage_options == recovered_path.storage_options


def test_copy_path():
    path = UPath("gcs://bucket/folder", token="anon")
    copy_path = UPath(path)

    assert type(path) is type(copy_path)
    assert str(path) == str(copy_path)
    assert path.drive == copy_path.drive
    assert path.root == copy_path.root
    assert path.parts == copy_path.parts
    assert path.storage_options == copy_path.storage_options


def test_copy_path_posix():
    path = UPath("/tmp/folder")
    copy_path = UPath(path)

    assert type(path) is type(copy_path)
    assert str(path) == str(copy_path)
    assert path.drive == copy_path.drive
    assert path.root == copy_path.root
    assert path.parts == copy_path.parts


def test_copy_path_append():
    path = UPath("/tmp/folder")
    copy_path = UPath(path, "folder2")

    assert type(path) is type(copy_path)
    assert str(path / "folder2") == str(copy_path)

    path = UPath("/tmp/folder")
    copy_path = UPath(path, "folder2/folder3")

    assert str(path / "folder2" / "folder3") == str(copy_path)

    path = UPath("/tmp/folder")
    copy_path = UPath(path, "folder2", "folder3")

    assert str(path / "folder2" / "folder3") == str(copy_path)


def test_compare_to_pathlib_path_ne():
    assert UPath("gcs://bucket/folder") != pathlib.Path("gcs://bucket/folder")
    assert pathlib.Path("gcs://bucket/folder") != UPath("gcs://bucket/folder")
    assert UPath("/bucket/folder") == pathlib.Path("/bucket/folder")
    assert pathlib.Path("/bucket/folder") == UPath("/bucket/folder")


def test_handle_fspath_args(tmp_path):
    f = tmp_path.joinpath("file.txt").as_posix()

    class X:
        def __str__(self):
            raise ValueError("should not be called")

        def __fspath__(self):
            return f

    assert UPath(X()).path == f


@pytest.mark.parametrize(
    "urlpath",
    [
        os.getcwd(),
        pathlib.Path.cwd().as_uri(),
        pytest.param(
            "mock:///abc",
            marks=pytest.mark.skipif(
                os.name == "nt",
                reason="_url not well defined for mock filesystem on windows",
            ),
        ),
    ],
)
def test_access_to_private_kwargs_and_url(urlpath):
    # fixme: this should be deprecated...
    pth = UPath(urlpath)
    with pytest.warns(DeprecationWarning, match="UPath._kwargs is deprecated"):
        assert isinstance(pth._kwargs, Mapping)
    with pytest.warns(DeprecationWarning, match="UPath._kwargs is deprecated"):
        assert pth._kwargs == {}
    assert isinstance(pth._url, SplitResult)
    assert pth._url.scheme == "" or pth._url.scheme in pth.fs.protocol
    assert pth._url.path == pth.path
    subpth = pth / "foo"
    with pytest.warns(DeprecationWarning, match="UPath._kwargs is deprecated"):
        assert subpth._kwargs == {}
    assert isinstance(subpth._url, SplitResult)
    assert subpth._url.scheme == "" or subpth._url.scheme in subpth.fs.protocol
    assert subpth._url.path == subpth.path


def test_copy_path_append_kwargs():
    path = UPath("gcs://bucket/folder", anon=True)
    copy_path = UPath(path, anon=False)

    assert type(path) is type(copy_path)
    assert str(path) == str(copy_path)
    assert not copy_path.storage_options["anon"]
    assert path.storage_options["anon"]


def test_relative_to():
    assert "s3://test_bucket/file.txt" == str(
        UPath("s3://test_bucket/file.txt").relative_to(UPath("s3://test_bucket"))
    )

    with pytest.raises(ValueError):
        UPath("s3://test_bucket/file.txt").relative_to(UPath("gcs://test_bucket"))

    with pytest.raises(ValueError):
        UPath("s3://test_bucket/file.txt", anon=True).relative_to(
            UPath("s3://test_bucket", anon=False)
        )


def test_uri_parsing():
    assert (
        str(UPath("http://www.example.com//a//b/")) == "http://www.example.com//a//b/"
    )


NORMALIZATIONS = (
    ("unnormalized", "normalized"),
    (
        # Expected normalization results according to curl
        ("http://example.com", "http://example.com/"),
        ("http://example.com/", "http://example.com/"),
        ("http://example.com/a", "http://example.com/a"),
        ("http://example.com//a", "http://example.com//a"),
        ("http://example.com///a", "http://example.com///a"),
        ("http://example.com////a", "http://example.com////a"),
        ("http://example.com/a/.", "http://example.com/a/"),
        ("http://example.com/a/./", "http://example.com/a/"),
        ("http://example.com/a/./b", "http://example.com/a/b"),
        ("http://example.com/a/.//", "http://example.com/a//"),
        ("http://example.com/a/.//b", "http://example.com/a//b"),
        ("http://example.com/a//.", "http://example.com/a//"),
        ("http://example.com/a//./", "http://example.com/a//"),
        ("http://example.com/a//./b", "http://example.com/a//b"),
        ("http://example.com/a//.//", "http://example.com/a///"),
        ("http://example.com/a//.//b", "http://example.com/a///b"),
        ("http://example.com/a/..", "http://example.com/"),
        ("http://example.com/a/../", "http://example.com/"),
        ("http://example.com/a/../.", "http://example.com/"),
        ("http://example.com/a/../..", "http://example.com/"),
        ("http://example.com/a/../../", "http://example.com/"),
        ("http://example.com/a/../..//", "http://example.com//"),
        ("http://example.com/a/..//", "http://example.com//"),
        ("http://example.com/a/..//.", "http://example.com//"),
        ("http://example.com/a/..//..", "http://example.com/"),
        ("http://example.com/a/../b", "http://example.com/b"),
        ("http://example.com/a/..//b", "http://example.com//b"),
        ("http://example.com/a//..", "http://example.com/a/"),
        ("http://example.com/a//../", "http://example.com/a/"),
        ("http://example.com/a//../.", "http://example.com/a/"),
        ("http://example.com/a//../..", "http://example.com/"),
        ("http://example.com/a//../../", "http://example.com/"),
        ("http://example.com/a//../..//", "http://example.com//"),
        ("http://example.com/a//..//..", "http://example.com/a/"),
        ("http://example.com/a//../b", "http://example.com/a/b"),
        ("http://example.com/a//..//", "http://example.com/a//"),
        ("http://example.com/a//..//.", "http://example.com/a//"),
        ("http://example.com/a//..//b", "http://example.com/a//b"),
        # Normalization with and without an authority component
        ("memory:/a/b/..", "memory://a/"),
        ("memory:/a/b/.", "memory://a/b/"),
        ("memory:/a/b/../..", "memory://"),
        ("memory:/a/b/../../..", "memory://"),
        ("memory://a/b/.", "memory://a/b/"),
        ("memory://a/b/..", "memory://a/"),
        ("memory://a/b/../..", "memory://"),
        ("memory://a/b/../../..", "memory://"),
        ("memory:///a/b/.", "memory://a/b/"),
        ("memory:///a/b/..", "memory://a/"),
        ("memory:///a/b/../..", "memory://"),
        ("memory:///a/b/../../..", "memory://"),
    ),
)


@pytest.mark.parametrize(*NORMALIZATIONS)
def test_normalize(unnormalized, normalized):
    expected = UPath(normalized)
    pth = UPath(unnormalized)
    if pth.protocol in {"http", "https"}:
        # Normalise only, do not attempt to follow redirects for http:// paths here
        result = pth.resolve(strict=True, follow_redirects=False)
    else:
        result = pth.resolve(strict=True)
    assert expected == result
    assert str(expected) == str(result)


@pytest.mark.parametrize(
    "uri,query_str",
    [
        ("s3://bucket/folder?versionId=1", "?versionId=1"),
        ("http://example.com/abc?p=2", "?p=2"),
    ],
)
def test_query_string(uri, query_str):
    p = UPath(uri)
    assert str(p).endswith(query_str)
    assert p.path.endswith(query_str)


@pytest.mark.parametrize(
    "base,join",
    [
        ("/a", "s3://bucket/b"),
        ("s3://bucket/a", "gs://b/c"),
        ("gs://bucket/a", "memory://b/c"),
        ("memory://bucket/a", "s3://b/c"),
    ],
)
def test_joinpath_on_protocol_mismatch(base, join):
    with pytest.raises(ValueError):
        UPath(base).joinpath(UPath(join))
    with pytest.raises(ValueError):
        UPath(base) / UPath(join)


@pytest.mark.parametrize(
    "base,join",
    [
        ("/a", "s3://bucket/b"),
        ("s3://bucket/a", "gs://b/c"),
        ("gs://bucket/a", "memory://b/c"),
        ("memory://bucket/a", "s3://b/c"),
    ],
)
def test_joinuri_on_protocol_mismatch(base, join):
    assert UPath(base).joinuri(UPath(join)) == UPath(join)


def test_upath_expanduser():
    assert UPath("~").expanduser() == UPath(os.path.expanduser("~"))
    assert UPath("~") != UPath("~").expanduser()
