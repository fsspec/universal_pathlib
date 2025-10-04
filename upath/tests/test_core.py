import os
import pathlib
import pickle
import sys
import warnings
from urllib.parse import SplitResult

import pathlib_abc
import pytest

from upath import UPath
from upath.implementations.cloud import GCSPath
from upath.implementations.cloud import S3Path
from upath.types import ReadablePath
from upath.types import WritablePath

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
        with pytest.raises(
            NotImplementedError,
            match=r".+Path[.]cwd\(\) is unsupported",
        ):
            type(self.path).cwd()

    def test_home(self):
        with pytest.raises(
            NotImplementedError,
            match=r".+Path[.]home\(\) is unsupported",
        ):
            type(self.path).home()

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
    assert str(path) == pathlib.Path(local_testdir).as_posix()
    assert issubclass(MyPath, UPath)
    assert isinstance(path, pathlib_abc.ReadablePath)
    assert isinstance(path, pathlib_abc.WritablePath)
    assert not isinstance(path, pathlib.Path)


def test_subclass_with_gcs():
    path = UPath("gcs://bucket", anon=True)
    assert isinstance(path, UPath)
    assert isinstance(path, ReadablePath)
    assert isinstance(path, WritablePath)
    assert not isinstance(path, os.PathLike)
    assert not isinstance(path, pathlib.Path)


def test_instance_check(local_testdir):
    path = UPath(local_testdir)
    # test instance check passes
    assert isinstance(path, UPath)
    assert isinstance(path, ReadablePath)
    assert isinstance(path, WritablePath)
    assert isinstance(path, os.PathLike)
    assert isinstance(path, pathlib.Path)


def test_instance_check_local_uri(local_testdir):
    path = UPath(f"file://{local_testdir}")
    assert isinstance(path, UPath)
    assert isinstance(path, ReadablePath)
    assert isinstance(path, WritablePath)
    assert isinstance(path, os.PathLike)
    assert not isinstance(path, pathlib.Path)


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
    p0 = UPath(urlpath)
    assert not hasattr(p0, "_kwargs")

    # fixme: this should be deprecated...
    assert isinstance(p0._url, SplitResult)
    assert p0._url.scheme == "" or p0._url.scheme in p0.fs.protocol
    assert p0._url.path == p0.path

    p1 = p0 / "foo"
    assert isinstance(p1._url, SplitResult)
    assert p1._url.scheme == "" or p1._url.scheme in p1.fs.protocol
    assert p1._url.path == p1.path


def test_copy_path_append_kwargs():
    path = UPath("gcs://bucket/folder", anon=True)
    copy_path = UPath(path, anon=False)

    assert type(path) is type(copy_path)
    assert str(path) == str(copy_path)
    assert not copy_path.storage_options["anon"]
    assert path.storage_options["anon"]


def test_relative_to():
    assert "file.txt" == str(
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
    result = pth.resolve(strict=True)
    str_expected = str(expected)
    str_result = str(result)
    assert expected == result
    assert str_expected == str_result


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


PROTOCOL_MISMATCH = [
    ("/a", "s3://bucket/b"),
    ("s3://bucket/a", "gs://b/c"),
    ("gs://bucket/a", "memory://b/c"),
    ("memory://bucket/a", "s3://b/c"),
]


@pytest.mark.parametrize("base,join", PROTOCOL_MISMATCH)
def test_joinpath_on_protocol_mismatch(base, join):
    with pytest.raises(ValueError, match="can't combine incompatible UPath protocols"):
        UPath(base).joinpath(UPath(join))


@pytest.mark.parametrize("base,join", PROTOCOL_MISMATCH)
def test_truediv_on_protocol_mismatch(base, join):
    with pytest.raises(ValueError, match="can't combine incompatible UPath protocols"):
        UPath(base) / UPath(join)


@pytest.mark.parametrize("base,join", PROTOCOL_MISMATCH)
def test_joinuri_on_protocol_mismatch(base, join):
    assert UPath(base).joinuri(UPath(join)) == UPath(join)


def test_upath_expanduser():
    assert UPath("~").expanduser() == UPath(os.path.expanduser("~"))
    assert UPath("~") != UPath("~").expanduser()


def test_builtin_open_a_non_local_upath():
    p = UPath("memory://a")
    p.write_bytes(b"hello world")
    with pytest.raises(TypeError, match="expected str, bytes or os.PathLike object.*"):
        open(p, "rb")  # type: ignore


@pytest.mark.parametrize(
    "protocol",
    [
        pytest.param(None, id="empty protocol"),
        pytest.param("file", id="file protocol"),
    ],
)
def test_open_a_local_upath(tmp_path, protocol):
    p = tmp_path.joinpath("file.txt")
    p.write_bytes(b"hello world")
    u = UPath(p, protocol=protocol)
    with open(u, "rb") as f:
        assert f.read() == b"hello world"


@pytest.mark.parametrize(
    "uri,protocol",
    [
        ("s3://bucket/folder", "s3"),
        ("gs://bucket/folder", "gs"),
        ("bucket/folder", "s3"),
        ("memory://folder", "memory"),
        ("file:/tmp/folder", "file"),
        ("/tmp/folder", "file"),
        ("/tmp/folder", ""),
        ("a/b/c", ""),
    ],
)
def test_constructor_compatible_protocol_uri(uri, protocol):
    p = UPath(uri, protocol=protocol)
    assert p.protocol == protocol


@pytest.mark.parametrize(
    "uri,protocol",
    [
        ("s3://bucket/folder", "gs"),
        ("gs://bucket/folder", "s3"),
        ("memory://folder", "s3"),
        ("file:/tmp/folder", "s3"),
        ("s3://bucket/folder", ""),
        ("memory://folder", ""),
        ("file:/tmp/folder", ""),
    ],
)
def test_constructor_incompatible_protocol_uri(uri, protocol):
    with pytest.raises(ValueError, match=r".*incompatible with"):
        UPath(uri, protocol=protocol)
