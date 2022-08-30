"""see upath/tests/conftest.py for fixtures
"""
import pytest  # noqa: F401

from upath import UPath
from upath.implementations.cloud import S3Path
from ..cases import BaseTests


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
            UPath("s3://test_bucket/file.txt").relative_to(
                UPath("s3://test_bucket")
            )
        )

    def test_iterdir_root(self):
        client_kwargs = self.path._kwargs["client_kwargs"]
        bucket_path = UPath(
            "s3://other_test_bucket", client_kwargs=client_kwargs
        )
        bucket_path.mkdir(mode="private")

        (bucket_path / "test1.txt").touch()
        (bucket_path / "test2.txt").touch()

        for x in bucket_path.iterdir():
            assert x.name != ""
            assert x.exists()

    def test_touch_unlink(self):
        path = self.path.joinpath("test_touch.txt")
        path.touch()
        assert path.exists()
        path.unlink()
        assert not path.exists()

        # should raise FileNotFoundError since file is missing
        with pytest.raises(FileNotFoundError):
            path.unlink()

        # file doesn't exists, but missing_ok is True
        path.unlink(missing_ok=True)

    @pytest.mark.parametrize(
        "joiner", [["bucket", "path", "file"], "bucket/path/file"]
    )
    def test_no_bucket_joinpath(self, joiner):
        path = UPath("s3://", anon=self.anon, **self.s3so)
        path = path.joinpath(joiner)
        assert str(path) == "s3://bucket/path/file"

    def test_creating_s3path_with_bucket(self):
        path = UPath("s3://", bucket="bucket", anon=self.anon, **self.s3so)
        assert str(path) == "s3://bucket/"
