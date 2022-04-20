"""see upath/tests/conftest.py for fixtures
"""
import pytest  # noqa: F401

from upath import UPath
from upath.errors import NotDirectoryError
from upath.implementations.s3 import S3Path
from ..cases import BaseTests


class TestUPathS3(BaseTests):
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

    def test_mkdir(self):
        new_dir = self.path.joinpath("new_dir")
        # new_dir.mkdir()
        # mkdir doesn't really do anything. A directory only exists in s3
        # if some file or something is written to it
        new_dir.joinpath("test.txt").touch()
        assert new_dir.exists()

    def test_rmdir(self, local_testdir):
        dirname = "rmdir_test"
        mock_dir = self.path.joinpath(dirname)
        mock_dir.joinpath("test.txt").touch()
        mock_dir.rmdir()
        assert not mock_dir.exists()
        with pytest.raises(NotDirectoryError):
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

    # def test_fsspec_compat(self):
    #     fs = self.path.fs
    #     scheme = self.path._url.scheme
    #     content = b"a,b,c\n1,2,3\n4,5,6"

    #     if not fs.exists(f"{scheme}://tmp"):
    #         fs.mkdir(f"{scheme}://tmp")

    #     p1 = f"{scheme}://tmp/output1.csv"
    #     upath1 = UPath(p1, anon=self.anon, **self.s3so)
    #     upath1.write_bytes(content)
    #     with fs.open(p1) as f:
    #         assert f.read() == content
    #     upath1.unlink()

    #     # write with fsspec, read with upath
    #     p2 = f"{scheme}://tmp/output2.csv"
    #     with fs.open(p2, "wb") as f:
    #         f.write(content)
    #     upath2 = UPath(p2, anon=self.anon, **self.s3so)
    #     assert upath2.read_bytes() == content
    #     upath2.unlink()

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
