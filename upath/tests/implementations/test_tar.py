import tarfile

import pytest

from upath import UPath
from upath.implementations.tar import TarPath

from ..cases import JoinablePathTests
from ..cases import NonWritablePathTests
from ..cases import ReadablePathTests
from ..utils import OverrideMeta
from ..utils import overrides_base


@pytest.fixture(scope="function")
def tarred_testdir_file(local_testdir, tmp_path_factory):
    base = tmp_path_factory.mktemp("tarpath")
    tar_path = base / "test.tar"
    with tarfile.TarFile(tar_path, "w") as tf:
        tf.add(local_testdir, arcname="", recursive=True)
    return str(tar_path)


class TestTarPath(
    JoinablePathTests,
    ReadablePathTests,
    NonWritablePathTests,
    metaclass=OverrideMeta,
):

    @pytest.fixture(autouse=True)
    def path(self, tarred_testdir_file):
        self.path = UPath("tar://", fo=tarred_testdir_file)
        # self.prepare_file_system()  done outside of UPath

    @overrides_base
    def test_is_correct_class(self):
        assert isinstance(self.path, TarPath)


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
