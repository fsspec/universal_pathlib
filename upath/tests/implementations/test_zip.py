import os
import zipfile

import pytest

from upath import UPath
from upath.implementations.zip import ZipPath

from ..cases import BaseTests


@pytest.fixture(scope="function")
def zipped_testdir_file(local_testdir, tmp_path_factory):
    base = tmp_path_factory.mktemp("zippath")
    zip_path = base / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for root, _, files in os.walk(local_testdir):
            for file in files:
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, start=local_testdir)
                zf.write(full_path, arcname=arcname)
    return str(zip_path)


@pytest.fixture(scope="function")
def empty_zipped_testdir_file(tmp_path):
    tmp_path = tmp_path.joinpath("zippath")
    tmp_path.mkdir()
    zip_path = tmp_path / "test.zip"

    with zipfile.ZipFile(zip_path, "w"):
        pass
    return str(zip_path)


class TestZipPath(BaseTests):

    @pytest.fixture(autouse=True)
    def path(self, zipped_testdir_file, request):
        try:
            (mode,) = request.param
        except (ValueError, TypeError, AttributeError):
            mode = "r"
        self.path = UPath("zip://", fo=zipped_testdir_file, mode=mode)
        # self.prepare_file_system()  done outside of UPath

    def test_is_ZipPath(self):
        assert isinstance(self.path, ZipPath)

    @pytest.mark.parametrize(
        "path", [("w",)], ids=["zipfile_mode_write"], indirect=True
    )
    def test_mkdir(self):
        super().test_mkdir()

    @pytest.mark.parametrize(
        "path", [("w",)], ids=["zipfile_mode_write"], indirect=True
    )
    def test_mkdir_exists_ok_true(self):
        super().test_mkdir_exists_ok_true()

    @pytest.mark.parametrize(
        "path", [("w",)], ids=["zipfile_mode_write"], indirect=True
    )
    def test_mkdir_exists_ok_false(self):
        super().test_mkdir_exists_ok_false()

    @pytest.mark.parametrize(
        "path", [("w",)], ids=["zipfile_mode_write"], indirect=True
    )
    def test_mkdir_parents_true_exists_ok_true(self):
        super().test_mkdir_parents_true_exists_ok_true()

    @pytest.mark.parametrize(
        "path", [("w",)], ids=["zipfile_mode_write"], indirect=True
    )
    def test_mkdir_parents_true_exists_ok_false(self):
        super().test_mkdir_parents_true_exists_ok_false()

    def test_rename(self):
        with pytest.raises(NotImplementedError):
            super().test_rename()  # delete is not implemented in fsspec

    def test_rename2(self):
        with pytest.raises(NotImplementedError):
            super().test_rename2()  # delete is not implemented in fsspec

    def test_move_local(self, tmp_path):
        with pytest.raises(NotImplementedError):
            super().test_move_local(tmp_path)  # delete is not implemented in fsspec

    def test_move_into_local(self, tmp_path):
        with pytest.raises(NotImplementedError):
            super().test_move_into_local(
                tmp_path
            )  # delete is not implemented in fsspec

    def test_move_memory(self, clear_fsspec_memory_cache):
        with pytest.raises(NotImplementedError):
            super().test_move_memory(clear_fsspec_memory_cache)

    def test_move_into_memory(self, clear_fsspec_memory_cache):
        with pytest.raises(NotImplementedError):
            super().test_move_into_memory(clear_fsspec_memory_cache)

    @pytest.mark.parametrize(
        "path", [("w",)], ids=["zipfile_mode_write"], indirect=True
    )
    def test_touch(self):
        super().test_touch()

    @pytest.mark.parametrize(
        "path", [("w",)], ids=["zipfile_mode_write"], indirect=True
    )
    def test_touch_unlink(self):
        with pytest.raises(NotImplementedError):
            super().test_touch_unlink()  # delete is not implemented in fsspec

    @pytest.mark.parametrize(
        "path", [("w",)], ids=["zipfile_mode_write"], indirect=True
    )
    def test_write_bytes(self):
        fn = "test_write_bytes.txt"
        s = b"hello_world"
        path = self.path.joinpath(fn)
        path.write_bytes(s)
        so = {**path.storage_options, "mode": "r"}
        urlpath = str(path)
        path.fs.close()
        assert UPath(urlpath, **so).read_bytes() == s

    @pytest.mark.parametrize(
        "path", [("w",)], ids=["zipfile_mode_write"], indirect=True
    )
    def test_write_text(self):
        fn = "test_write_text.txt"
        s = "hello_world"
        path = self.path.joinpath(fn)
        path.write_text(s)
        so = {**path.storage_options, "mode": "r"}
        urlpath = str(path)
        path.fs.close()
        assert UPath(urlpath, **so).read_text() == s

    @pytest.mark.skip(reason="fsspec zipfile filesystem is either read xor write mode")
    def test_fsspec_compat(self):
        pass


@pytest.fixture(scope="function")
def zipped_testdir_file_in_memory(zipped_testdir_file, clear_fsspec_memory_cache):
    p = UPath(zipped_testdir_file, protocol="file")
    t = p.move(UPath("memory:///myzipfile.zip"))
    assert t.protocol == "memory"
    assert t.exists()
    yield t.as_uri()


class TestChainedZipPath(TestZipPath):

    @pytest.fixture(autouse=True)
    def path(self, zipped_testdir_file_in_memory, request):
        try:
            (mode,) = request.param
        except (ValueError, TypeError, AttributeError):
            mode = "r"
        self.path = UPath(
            "zip://", fo="/myzipfile.zip", mode=mode, target_protocol="memory"
        )
