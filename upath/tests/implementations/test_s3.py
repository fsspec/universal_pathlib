"""see upath/tests/conftest.py for fixtures
"""

import sys

import fsspec
import pytest  # noqa: F401

from upath import UPath
from upath.implementations.cloud import S3Path

from ..cases import BaseTests


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
class TestUPathS3(BaseTests):
    SUPPORTS_EMPTY_DIRS = False

    @pytest.fixture(autouse=True)
    def path(self, s3_fixture):
        path, anon, s3so = s3_fixture
        self.path = UPath(path, anon=anon, **s3so)
        self.anon = anon
        self.s3so = s3so

    def test_is_S3Path(self):
        assert isinstance(self.path, S3Path)

    def test_chmod(self):
        # todo
        pass

    def test_rmdir(self):
        dirname = "rmdir_test"
        mock_dir = self.path.joinpath(dirname)
        mock_dir.joinpath("test.txt").touch()
        mock_dir.rmdir()
        assert not mock_dir.exists()
        with pytest.raises(NotADirectoryError):
            self.path.joinpath("file1.txt").rmdir()

    def test_relative_to(self):
        assert "s3://test_bucket/file.txt" == str(
            UPath("s3://test_bucket/file.txt").relative_to(UPath("s3://test_bucket"))
        )

    def test_iterdir_root(self):
        client_kwargs = self.path.storage_options["client_kwargs"]
        bucket_path = UPath("s3://other_test_bucket", client_kwargs=client_kwargs)
        bucket_path.mkdir()

        (bucket_path / "test1.txt").touch()
        (bucket_path / "test2.txt").touch()

        for x in bucket_path.iterdir():
            assert x.name != ""
            assert x.exists()

    @pytest.mark.parametrize(
        "joiner", [["bucket", "path", "file"], ["bucket/path/file"]]
    )
    def test_no_bucket_joinpath(self, joiner):
        path = UPath("s3://", anon=self.anon, **self.s3so)
        path = path.joinpath(*joiner)
        assert str(path) == "s3://bucket/path/file"

    def test_creating_s3path_with_bucket(self):
        path = UPath("s3://", bucket="bucket", anon=self.anon, **self.s3so)
        assert str(path) == "s3://bucket/"

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

    @pytest.mark.skip
    def test_makedirs_exist_ok_false(self):
        pass


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
                    s3.rm(f"{dir}/{key}")


def test_path_with_hash_and_space():
    assert "with#hash and space" in UPath("s3://bucket/with#hash and space/abc").parts


def test_pathlib_consistent_join():
    b0 = UPath("s3://mybucket/withkey/").joinpath("subfolder/myfile.txt")
    b1 = UPath("s3://mybucket/withkey").joinpath("subfolder/myfile.txt")
    assert b0 == b1
    assert "s3://mybucket/withkey/subfolder/myfile.txt" == str(b0) == str(b1)
