"""see upath/tests/conftest.py for fixtures
"""
import pytest  # noqa: F401

from upath import UPath
from upath.errors import NotDirectoryError
from upath.implementations.s3 import S3Path
from upath.tests.test_core import TestUpath


class TestUPathS3(TestUpath):
    @pytest.fixture(autouse=True)
    def path(self, local_testdir, s3):
        anon, s3so = s3
        path = f"s3:{local_testdir}"
        self.path = UPath(path, anon=anon, **s3so)

    def test_is_S3Path(self):
        assert isinstance(self.path, S3Path)

    def test_chmod(self):
        # todo
        pass

    def test_mkdir(self):
        new_dir = self.path.joinpath("new_dir")
        # new_dir.mkdir()
        # mkdir doesnt really do anything. A directory only exists in s3
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
