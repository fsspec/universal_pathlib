import pytest

from upath import UPath
from upath.implementations.cached import SimpleCachePath

from ..cases import BaseTests


class TestSimpleCachePath(BaseTests):
    @pytest.fixture(autouse=True)
    def path(self, local_testdir):
        if not local_testdir.startswith("/"):
            local_testdir = "/" + local_testdir
        path = f"simplecache::memory:{local_testdir}"
        self.path = UPath(path)
        self.prepare_file_system()

    def test_is_SimpleCachePath(self):
        assert isinstance(self.path, SimpleCachePath)
