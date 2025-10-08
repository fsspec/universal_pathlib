import tarfile

import pytest

from upath import UPath
from upath.implementations.tar import TarPath

from ..cases import BaseTests


@pytest.fixture(scope="function")
def tarred_testdir_file(local_testdir, tmp_path_factory):
    base = tmp_path_factory.mktemp("tarpath")
    tar_path = base / "test.tar"
    with tarfile.TarFile(tar_path, "w") as tf:
        tf.add(local_testdir, arcname="", recursive=True)
    return str(tar_path)


class TestTarPath(BaseTests):

    @pytest.fixture(autouse=True)
    def path(self, tarred_testdir_file):
        self.path = UPath("tar://", fo=tarred_testdir_file)
        # self.prepare_file_system()  done outside of UPath

    def test_is_TarPath(self):
        assert isinstance(self.path, TarPath)

    @pytest.mark.skip(reason="Tar filesystem is read-only")
    def test_mkdir(self):
        pass

    @pytest.mark.skip(reason="Tar filesystem is read-only")
    def test_mkdir_exists_ok_false(self):
        pass

    @pytest.mark.skip(reason="Tar filesystem is read-only")
    def test_mkdir_parents_true_exists_ok_false(self):
        pass

    @pytest.mark.skip(reason="Tar filesystem is read-only")
    def test_rename(self):
        pass

    @pytest.mark.skip(reason="Tar filesystem is read-only")
    def test_rename2(self):
        pass

    @pytest.mark.skip(reason="Tar filesystem is read-only")
    def test_touch(self):
        pass

    @pytest.mark.skip(reason="Tar filesystem is read-only")
    def test_touch_unlink(self):
        pass

    @pytest.mark.skip(reason="Tar filesystem is read-only")
    def test_write_bytes(self):
        pass

    @pytest.mark.skip(reason="Tar filesystem is read-only")
    def test_write_text(self):
        pass

    @pytest.mark.skip(reason="Tar filesystem is read-only")
    def test_fsspec_compat(self):
        pass

    @pytest.mark.skip(reason="Only testing read on TarPath")
    def test_move_local(self, tmp_path):
        pass

    @pytest.mark.skip(reason="Only testing read on TarPath")
    def test_move_into_local(self, tmp_path):
        pass

    @pytest.mark.skip(reason="Only testing read on TarPath")
    def test_move_memory(self, clear_fsspec_memory_cache):
        pass

    @pytest.mark.skip(reason="Only testing read on TarPath")
    def test_move_into_memory(self, clear_fsspec_memory_cache):
        pass


@pytest.fixture(scope="function")
def tarred_testdir_file_in_memory(tarred_testdir_file, clear_fsspec_memory_cache):
    p = UPath(tarred_testdir_file, protocol="file")
    t = p.move(UPath("memory:///mytarfile.tar"))
    assert t.protocol == "memory"
    assert t.exists()
    yield t.as_uri()


class TestChainedTarPath(TestTarPath):

    @pytest.fixture(autouse=True)
    def path(self, tarred_testdir_file_in_memory):
        self.path = UPath("tar://::memory:///mytarfile.tar")
