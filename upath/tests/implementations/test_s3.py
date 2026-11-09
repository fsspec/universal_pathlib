"""see upath/tests/conftest.py for fixtures"""

import pickle
import sys
import warnings

import fsspec
import pytest

from upath import UPath
from upath.implementations.cloud import S3HttpPath
from upath.implementations.cloud import S3Path

from ..cases import BaseTests
from ..utils import OverrideMeta
from ..utils import extends_base
from ..utils import overrides_base
from ..utils import posixify


def silence_botocore_datetime_deprecation(cls):
    # botocore uses datetime.datetime.utcnow in 3.12 which is deprecated
    # see: https://github.com/boto/boto3/issues/3889#issuecomment-1751296363
    if sys.version_info >= (3, 12):
        return pytest.mark.filterwarnings(
            "ignore"
            r":datetime.datetime.utcnow\(\) is deprecated"
            ":DeprecationWarning"
        )(cls)
    else:
        return cls


@silence_botocore_datetime_deprecation
class TestUPathS3(BaseTests, metaclass=OverrideMeta):
    SUPPORTS_EMPTY_DIRS = False

    @pytest.fixture(autouse=True)
    def path(self, s3_fixture):
        path, anon, s3so = s3_fixture
        self.path = UPath(path, anon=anon, **s3so)
        self.anon = anon
        self.s3so = s3so

    @overrides_base
    def test_is_correct_class(self):
        assert isinstance(self.path, S3Path)

    @extends_base
    def test_rmdir(self):
        dirname = "rmdir_test"
        mock_dir = self.path.joinpath(dirname)
        mock_dir.joinpath("test.txt").touch()
        mock_dir.rmdir()
        assert not mock_dir.exists()
        with pytest.raises(NotADirectoryError):
            self.path.joinpath("file1.txt").rmdir()

    @extends_base
    def test_relative_to_extra(self):
        assert "file.txt" == str(
            UPath("s3://test_bucket/file.txt").relative_to(UPath("s3://test_bucket"))
        )

    @extends_base
    def test_iterdir_root(self):
        client_kwargs = self.path.storage_options["client_kwargs"]
        bucket_path = UPath("s3://other_test_bucket", client_kwargs=client_kwargs)
        bucket_path.mkdir()

        (bucket_path / "test1.txt").touch()
        (bucket_path / "test2.txt").touch()

        for x in bucket_path.iterdir():
            assert x.name != ""
            assert x.exists()

    @extends_base
    @pytest.mark.parametrize(
        "joiner", [["bucket", "path", "file"], ["bucket/path/file"]]
    )
    def test_no_bucket_joinpath(self, joiner):
        path = UPath("s3://", anon=self.anon, **self.s3so)
        path = path.joinpath(*joiner)
        assert str(path) == "s3://bucket/path/file"

    @extends_base
    def test_creating_s3path_with_bucket(self):
        path = UPath("s3://", bucket="bucket", anon=self.anon, **self.s3so)
        assert str(path) == "s3://bucket/"

    @extends_base
    def test_iterdir_with_plus_in_name(self, s3_with_plus_chr_name):
        bucket, anon, s3so = s3_with_plus_chr_name
        p = UPath(
            f"s3://{bucket}/manual__2022-02-19T14:31:25.891270+00:00",
            anon=True,
            **s3so,
        )

        files = list(p.iterdir())
        assert len(files) == 1
        (file,) = files
        assert file == p.joinpath("file.txt")

    @extends_base
    @pytest.mark.xfail(reason="fsspec/universal_pathlib#144")
    def test_rglob_with_double_fwd_slash(self, s3_with_double_fwd_slash_files):
        import boto3
        import botocore.exceptions

        bucket, anon, s3so = s3_with_double_fwd_slash_files

        conn = boto3.resource("s3", **s3so["client_kwargs"])
        # ensure there's no s3://bucket/key.txt object
        with pytest.raises(botocore.exceptions.ClientError, match=".*Not Found.*"):
            conn.Object(bucket, "key.txt").load()
        # ensure there's a s3://bucket//key.txt object
        assert conn.Object(bucket, "/key.txt").get()["Body"].read() == b"hello world"

        p0 = UPath(f"s3://{bucket}//key.txt", **s3so)
        assert p0.read_bytes() == b"hello world"
        p1 = UPath(f"s3://{bucket}", **s3so)
        assert list(p1.rglob("*.txt")) == [p0]


@pytest.fixture
def s3_with_plus_chr_name(s3_server):
    anon, s3so = s3_server
    s3 = fsspec.filesystem("s3", anon=False, **s3so)
    bucket = "plus_chr_bucket"
    path = f"{bucket}/manual__2022-02-19T14:31:25.891270+00:00"
    s3.mkdir(path)
    s3.touch(f"{path}/file.txt")
    s3.invalidate_cache()
    try:
        yield bucket, anon, s3so
    finally:
        if s3.exists(bucket):
            for dir, _, keys in s3.walk(bucket):
                for key in keys:
                    if key.rstrip("/"):
                        s3.rm(f"{dir}/{key}")


@pytest.fixture
def s3_with_double_fwd_slash_files(s3_server):
    anon, s3so = s3_server
    s3 = fsspec.filesystem("s3", anon=False, **s3so)
    bucket = "double_fwd_slash_bucket"
    s3.mkdir(bucket + "/")
    s3.pipe_file(f"{bucket}//key.txt", b"hello world")
    try:
        yield bucket, anon, s3so
    finally:
        if s3.exists(bucket):
            for dir, _, keys in s3.walk(bucket):
                for key in keys:
                    if key.rstrip("/"):
                        s3.rm(f"{dir}/{key}")


def test_path_with_hash_and_space():
    assert "with#hash and space" in UPath("s3://bucket/with#hash and space/abc").parts


def test_pathlib_consistent_join():
    b0 = UPath("s3://mybucket/withkey/").joinpath("subfolder/myfile.txt")
    b1 = UPath("s3://mybucket/withkey").joinpath("subfolder/myfile.txt")
    assert b0 == b1
    assert "s3://mybucket/withkey/subfolder/myfile.txt" == str(b0) == str(b1)


def test_copy__object_key_collides_with_dir_prefix(s3_server, tmp_path):
    pytest.importorskip("s3fs")
    anon, s3so = s3_server

    s3 = fsspec.filesystem("s3", anon=anon, **{**s3so, "use_listings_cache": False})
    bucket = "copy_into_collision_bucket"
    s3.mkdir(bucket + "/src" + "/common_prefix/")
    # object under common prefix as key
    s3.pipe_file(f"{bucket}/src/common_prefix", b"hello world")
    # store more objects with same prefix
    s3.pipe_file(f"{bucket}/src/common_prefix/file1.txt", b"1")
    s3.pipe_file(f"{bucket}/src/common_prefix/file2.txt", b"2")

    # make sure the sources have a collision
    assert s3.isdir(f"{bucket}/src/common_prefix")
    assert s3.isfile(f"{bucket}/src/common_prefix")
    assert s3.isfile(f"{bucket}/src/common_prefix/file1.txt")
    assert s3.isfile(f"{bucket}/src/common_prefix/file2.txt")
    # prepare source and destination
    src = UPath(f"s3://{bucket}/src", anon=anon, **s3so)
    dst = UPath(tmp_path)

    def on_collision_rename_file(src, dst):
        warnings.warn(
            f"{src!s} collides with prefix. Renaming target file object to {dst!s}",
            UserWarning,
            stacklevel=3,
        )
        return (
            dst.with_suffix(dst.suffix + ".COLLISION"),
            dst,
        )

    # perform copy
    src.copy_into(dst, on_name_collision=on_collision_rename_file)

    # check results
    dst_files = sorted(posixify(x.relative_to(tmp_path)) for x in dst.glob("**/*"))
    assert dst_files == [
        "src",
        "src/common_prefix",
        "src/common_prefix.COLLISION",
        "src/common_prefix/file1.txt",
        "src/common_prefix/file2.txt",
    ]


@silence_botocore_datetime_deprecation
class TestUPathS3Http(BaseTests, metaclass=OverrideMeta):
    SUPPORTS_EMPTY_DIRS = False

    @pytest.fixture(autouse=True)
    def path(self, s3_fixture):
        path, anon, s3so = s3_fixture
        s3so = dict(s3so)
        endpoint_url = s3so.pop("client_kwargs")["endpoint_url"].rstrip("/")
        url = path.replace("s3://", f"s3+{endpoint_url}/")
        self.path = UPath(url, anon=anon, **s3so)
        self.endpoint_url = endpoint_url

    @overrides_base
    def test_is_correct_class(self):
        assert isinstance(self.path, S3HttpPath)
        assert isinstance(self.path, S3Path)

    @overrides_base
    def test_protocol(self):
        # fsspec doesn't know about s3+http(s), the filesystem is s3fs
        assert self.path.protocol == f"s3+{self.endpoint_url.partition(':')[0]}"
        assert type(self.path.fs) is fsspec.get_filesystem_class("s3")

    @overrides_base
    def test_read_with_fsspec(self):
        p = self.path_file
        fs = fsspec.filesystem("s3", **p.storage_options)
        with fs.open(p.path) as f:
            assert f.read() == b"hello world"

    @extends_base
    def test_str_roundtrip(self):
        url = f"s3+{self.endpoint_url}/test_bucket/folder1/file1.txt"
        p = self.path.joinpath("folder1", "file1.txt")
        assert str(p) == p.as_uri() == url
        assert str(p.parent) == url.removesuffix("/file1.txt")
        assert UPath(str(p), **self.path.storage_options) == p
        assert p.storage_options["endpoint_url"] == self.endpoint_url

    @extends_base
    def test_iterdir_str(self):
        prefix = f"s3+{self.endpoint_url}/test_bucket/"
        assert all(str(x).startswith(prefix) for x in self.path.iterdir())


@pytest.mark.parametrize(
    "url,protocol,endpoint_url,path",
    [
        (
            "s3+https://example.com/bucket/a/b.txt",
            "s3+https",
            "https://example.com",
            "bucket/a/b.txt",
        ),
        (
            "s3+http://localhost:9000/bucket/a",
            "s3+http",
            "http://localhost:9000",
            "bucket/a",
        ),
        (
            "s3+http://localhost:9000/bucket/",
            "s3+http",
            "http://localhost:9000",
            "bucket/",
        ),
        ("s3+https://example.com/", "s3+https", "https://example.com", ""),
    ],
)
def test_s3_http_url(url, protocol, endpoint_url, path):
    p = UPath(url)
    assert isinstance(p, S3HttpPath)
    assert p.protocol == protocol
    assert p.path == path
    assert p.storage_options["endpoint_url"] == endpoint_url
    assert str(p) == url
    assert UPath(str(p)) == p
    assert pickle.loads(pickle.dumps(p)) == p
    if path:
        assert str(p / "c") == f"{url.rstrip('/')}/c"
    else:
        assert str(p / "c") == f"{url}c/"  # bucket


def test_s3_http_url_from_storage_options():
    p = UPath("bucket/a", protocol="s3+https", endpoint_url="https://example.com")
    assert str(p) == "s3+https://example.com/bucket/a"


def test_s3_http_url_conflicting_endpoint_url():
    with pytest.raises(ValueError, match="conflicts"):
        UPath("s3+https://example.com/bucket/a", endpoint_url="https://other.com")


def test_s3_http_url_requires_endpoint_url():
    with pytest.raises(ValueError, match="endpoint_url"):
        UPath("bucket/a", protocol="s3+https")


@pytest.mark.parametrize(
    "endpoint_url", ["http://example.com", "https://example.com/prefix"]
)
def test_s3_http_url_inexpressible_endpoint_url(endpoint_url):
    with pytest.raises(ValueError, match="can't be expressed"):
        UPath("bucket/a", protocol="s3+https", endpoint_url=endpoint_url)
