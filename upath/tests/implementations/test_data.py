import stat

import fsspec
import pytest

from upath import UPath
from upath.implementations.data import DataPath
from upath.tests.cases import BaseTests

from ..utils import xfail_if_version

pytestmark = xfail_if_version(
    "fsspec", lt="2023.12.2", reason="fsspec<2023.12.2 does not support data"
)


class TestUPathDataPath(BaseTests):
    """
    Unit-tests for the DataPath implementation of UPath.
    """

    @pytest.fixture(autouse=True)
    def path(self):
        """
        Fixture for the UPath instance to be tested.
        """
        path = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVQI12PYeuECAASTAlbqXbfWAAAAAElFTkSuQmCC"  # noqa: E501
        self.path = UPath(path)

    def test_is_DataPath(self):
        """
        Test that the path is a GitHubPath instance.
        """
        assert isinstance(self.path, DataPath)

    @pytest.mark.skip(reason="DataPath does not have directories")
    def test_stat_dir_st_mode(self):
        super().test_stat_dir_st_mode()

    def test_stat_file_st_mode(self):
        assert self.path.is_file()
        assert stat.S_ISREG(self.path.stat().st_mode)

    def test_stat_st_size(self):
        assert self.path.stat().st_size == 69

    def test_exists(self):
        # datapath exists is always true...
        path = self.path
        assert path.exists()

    @pytest.mark.skip(reason="DataPath does support joins or globs")
    def test_glob(self, pathlib_base):
        with pytest.raises(NotImplementedError):
            pathlib_base.glob("*")

    def test_is_dir(self):
        assert not self.path.is_dir()

    def test_is_file(self):
        assert self.path.is_file()

    def test_iterdir(self):
        with pytest.raises(NotImplementedError):
            list(self.path.iterdir())

    @pytest.mark.skip(reason="DataPath does not have directories")
    def test_iterdir2(self):
        pass

    @pytest.mark.skip(reason="DataPath does not have directories")
    def test_iterdir_trailing_slash(self):
        pass

    def test_mkdir(self):
        with pytest.raises(FileExistsError):
            self.path.mkdir()

    @pytest.mark.skip(reason="DataPath does not have directories")
    def test_mkdir_exists_ok_true(self):
        pass

    @pytest.mark.skip(reason="DataPath does not have directories")
    def test_mkdir_exists_ok_false(self):
        pass

    @pytest.mark.skip(reason="DataPath does not have directories")
    def test_mkdir_parents_true_exists_ok_true(self):
        pass

    @pytest.mark.skip(reason="DataPath does not have directories")
    def test_mkdir_parents_true_exists_ok_false(self):
        pass

    def test_open(self):
        p = UPath("data:text/plain;base64,aGVsbG8gd29ybGQ=")
        with p.open(mode="r") as f:
            assert f.read() == "hello world"
        with p.open(mode="rb") as f:
            assert f.read() == b"hello world"

    def test_open_buffering(self):
        self.path.open(buffering=-1)

    def test_open_block_size(self):
        p = UPath("data:text/plain;base64,aGVsbG8gd29ybGQ=")
        with p.open(mode="r", block_size=8192) as f:
            assert f.read() == "hello world"

    def test_open_errors(self):
        p = UPath("data:text/plain;base64,aGVsbG8gd29ybGQ=")
        with p.open(mode="r", encoding="ascii", errors="strict") as f:
            assert f.read() == "hello world"

    def test_read_bytes(self, pathlib_base):
        assert len(self.path.read_bytes()) == 69

    def test_read_text(self, local_testdir):
        assert UPath("data:base64,SGVsbG8gV29ybGQ=").read_text() == "Hello World"

    def test_parents(self):
        with pytest.raises(NotImplementedError):
            self.path.parents[0]

    def test_rename(self):
        with pytest.raises(NotImplementedError):
            self.path.rename("newname")

    def test_rename2(self):
        self.path.rename(self.path)

    def test_rglob(self, pathlib_base):
        with pytest.raises(NotImplementedError):
            list(self.path.rglob("*"))

    def test_touch_exists_ok_false(self):
        with pytest.raises(FileExistsError):
            self.path.touch(exist_ok=False)

    def test_touch_exists_ok_true(self):
        self.path.touch()

    def test_touch_unlink(self):
        self.path.touch()
        with pytest.raises(NotImplementedError):
            self.path.unlink()

    def test_write_bytes(self, pathlib_base):
        with pytest.raises(NotImplementedError):
            self.path.write_bytes(b"test")

    def test_write_text(self, pathlib_base):
        with pytest.raises(NotImplementedError):
            self.path.write_text("test")

    def test_read_with_fsspec(self):
        pth = self.path
        fs = fsspec.filesystem(pth.protocol, **pth.storage_options)
        assert fs.cat_file(pth.path) == pth.read_bytes()

    @pytest.mark.skip(reason="DataPath does not support joins")
    def test_pickling_child_path(self):
        pass

    @pytest.mark.skip(reason="DataPath does not support joins")
    def test_child_path(self):
        pass

    def test_with_name(self):
        with pytest.raises(NotImplementedError):
            self.path.with_name("newname")

    def test_with_suffix(self):
        with pytest.raises(NotImplementedError):
            self.path.with_suffix(".new")

    def test_with_stem(self):
        with pytest.raises(NotImplementedError):
            self.path.with_stem("newname")

    @pytest.mark.skip(reason="DataPath does not support joins")
    def test_repr_after_with_suffix(self):
        pass

    @pytest.mark.skip(reason="DataPath does not support joins")
    def test_repr_after_with_name(self):
        pass

    @pytest.mark.skip(reason="DataPath does not support directories")
    def test_rmdir_no_dir(self):
        pass

    @pytest.mark.skip(reason="DataPath does not support directories")
    def test_iterdir_no_dir(self):
        pass

    @pytest.mark.skip(reason="DataPath does not support joins")
    def test_private_url_attr_in_sync(self):
        pass

    @pytest.mark.skip(reason="DataPath does not support joins")
    def test_fsspec_compat(self):
        pass

    def test_rmdir_not_empty(self):
        with pytest.raises(NotADirectoryError):
            self.path.rmdir()

    def test_samefile(self):
        f1 = self.path

        assert f1.samefile(f1) is True
