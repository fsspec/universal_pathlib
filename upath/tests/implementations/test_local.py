import pytest

from upath import UPath
from upath.implementations.local import LocalPath
from upath.tests.cases import BaseTests
from upath.tests.utils import skip_on_windows


@skip_on_windows
class TestFSSpecLocal(BaseTests):
    @pytest.fixture(autouse=True)
    def path(self, local_testdir):
        path = f"file://{local_testdir}"
        self.path = UPath(path)

    def test_is_LocalPath(self):
        assert isinstance(self.path, LocalPath)
