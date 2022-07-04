from pathlib import Path

import pytest  # noqa: F401
from upath import UPath

from ..cases import BaseTests


class TestUPathZip(BaseTests):
    @pytest.fixture(autouse=True, scope="function")
    def path(self, zip_fixture):
        self.path = UPath(f"zip://{zip_fixture}")

    def test_stat(self):
        # self.path.stat() doesn't make sense?
        assert (self.path / "file1.txt").stat()

    def test_is_dir(self):
        # self.path.is_dir() doesn't make sense?
        assert (self.path / "folder1").is_dir()

    def test_is_file(self):
        path = self.path / "file1.txt"
        assert path.is_file()
        # assert not self.path.is_file()

        assert not (self.path / "not-existing-file.txt").is_file()

    def test_iterdir(self, local_testdir):
        pl_path = Path(local_testdir)

        up_iter = list(self.path.iterdir())
        pl_iter = list(pl_path.iterdir())

        for x in up_iter:
            assert x.name != ""
            assert x.exists()

        assert len(up_iter) == len(pl_iter)
        assert set(p.name for p in pl_iter) == set(u.name for u in up_iter)
        # assert next(self.path.parent.iterdir()).exists()

    def test_iterdir2(self, local_testdir):
        pl_path = Path(local_testdir) / "folder1"

        up_iter = list((self.path / "folder1").iterdir())
        pl_iter = list(pl_path.iterdir())

        for x in up_iter:
            assert x.exists()

        assert len(up_iter) == len(pl_iter)
        assert set(p.name for p in pl_iter) == set(u.name for u in up_iter)
        # assert next(self.path.parent.iterdir()).exists()

    @pytest.mark.xfail(
        reason="Current fsspec ZipFileSystem implementation is read only"
    )
    def test_mkdir(self):
        super().test_mkdir()

    @pytest.mark.xfail(
        reason="Current fsspec ZipFileSystem implementation is read only"
    )
    def test_touch_unlink(self):
        super().test_touch_unlink()

    @pytest.mark.xfail(
        reason="Current fsspec ZipFileSystem implementation is read only"
    )
    def test_write_bytes(self, pathlib_base):
        return super().test_write_bytes(pathlib_base)

    @pytest.mark.xfail(
        reason="Current fsspec ZipFileSystem implementation is read only"
    )
    def test_write_text(self, pathlib_base):
        return super().test_write_text(pathlib_base)

    @pytest.mark.xfail(
        reason="Current fsspec ZipFileSystem implementation is read only"
    )
    def test_fsspec_compat(self):
        return super().test_fsspec_compat()
