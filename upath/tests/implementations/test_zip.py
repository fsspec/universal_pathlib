import os
import zipfile

import pytest

from upath import UnsupportedOperation
from upath import UPath
from upath.implementations.zip import ZipPath

from ..cases import JoinablePathTests
from ..cases import NonWritablePathTests
from ..cases import ReadablePathTests
from ..utils import OverrideMeta
from ..utils import extends_base
from ..utils import overrides_base


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


class TestZipPath(
    JoinablePathTests,
    ReadablePathTests,
    NonWritablePathTests,
    metaclass=OverrideMeta,
):
    @pytest.fixture(autouse=True)
    def path(self, zipped_testdir_file, request):
        try:
            (mode,) = request.param
        except (ValueError, TypeError, AttributeError):
            mode = "r"
        self.path = UPath("zip://", fo=zipped_testdir_file, mode=mode)
        try:
            yield
        finally:
            self.path.fs.clear_instance_cache()

    @overrides_base
    def test_is_correct_class(self):
        assert isinstance(self.path, ZipPath)

    @extends_base
    def test_write_mode_is_disabled(self, tmp_path):
        with pytest.raises(UnsupportedOperation):
            UPath("zip://", fo=tmp_path.joinpath("myzip.zip"), mode="a")
        with pytest.raises(UnsupportedOperation):
            UPath("zip://", fo=tmp_path.joinpath("myzip.zip"), mode="x")
        with pytest.raises(UnsupportedOperation):
            UPath("zip://", fo=tmp_path.joinpath("myzip.zip"), mode="w")


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
