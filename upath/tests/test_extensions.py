import pytest

from upath.extensions import ProxyUPath
from upath.implementations.local import FilePath
from upath.implementations.memory import MemoryPath
from upath.tests.cases import BaseTests


class TestProxyMemoryPath(BaseTests):
    @pytest.fixture(autouse=True)
    def path(self, local_testdir):
        if not local_testdir.startswith("/"):
            local_testdir = "/" + local_testdir
        self.path = ProxyUPath(f"memory:{local_testdir}")
        self.prepare_file_system()

    def test_is_ProxyUPath(self):
        assert isinstance(self.path, ProxyUPath)

    def test_is_not_MemoryPath(self):
        assert not isinstance(self.path, MemoryPath)


class TestProxyFilePath(BaseTests):
    @pytest.fixture(autouse=True)
    def path(self, local_testdir):
        self.path = ProxyUPath(f"file://{local_testdir}")
        self.prepare_file_system()

    def test_is_ProxyUPath(self):
        assert isinstance(self.path, ProxyUPath)

    def test_is_not_FilePath(self):
        assert not isinstance(self.path, FilePath)


def test_custom_subclass():

    class ReversePath(ProxyUPath):
        def read_bytes_reversed(self):
            return self.read_bytes()[::-1]

        def write_bytes_reversed(self, value):
            self.write_bytes(value[::-1])

    b = MemoryPath("memory://base")

    p = b.joinpath("file1")
    p.write_bytes(b"dlrow olleh")

    r = ReversePath("memory://base/file1")
    assert r.read_bytes_reversed() == b"hello world"

    r.parent.joinpath("file2").write_bytes_reversed(b"dlrow olleh")
    assert b.joinpath("file2").read_bytes() == b"hello world"
