import pytest

from upath import UPath
from upath.implementations.local import LocalPath
from upath.tests.cases import BaseTests
from upath.tests.utils import xfail_if_version


class TestFSSpecLocal(BaseTests):
    @pytest.fixture(autouse=True)
    def path(self, local_testdir):
        path = f"file://{local_testdir}"
        self.path = UPath(path)

    def test_is_LocalPath(self):
        assert isinstance(self.path, LocalPath)


@xfail_if_version("fsspec", lt="2023.10.0", reason="requires fsspec>=2023.10.0")
class TestRayIOFSSpecLocal(BaseTests):
    @pytest.fixture(autouse=True)
    def path(self, local_testdir):
        path = f"local://{local_testdir}"
        self.path = UPath(path)

    def test_is_LocalPath(self):
        assert isinstance(self.path, LocalPath)
