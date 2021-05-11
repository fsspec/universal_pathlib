"""see upath/tests/conftest.py for fixtures
"""
import pytest  # noqa: F401

from upath import UPath
from upath.implementations.hdfs import HDFSPath
from upath.tests.cases import BaseTests


@pytest.mark.hdfs
class TestUPathHDFS(BaseTests):
    @pytest.fixture(autouse=True)
    def path(self, local_testdir, hdfs):
        host, user, port = hdfs
        path = f"hdfs:{local_testdir}"
        self.path = UPath(path, host=host, user=user, port=port)

    def test_is_HDFSPath(self):
        assert isinstance(self.path, HDFSPath)

    def test_chmod(self):
        # todo
        pass

    def test_fsspec_compat(self):
        pass
