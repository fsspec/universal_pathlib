import pytest

from upath import UPath
from upath.tests.cases import BaseTests
from upath.tests.utils import skip_on_windows


@skip_on_windows
class TestUPathSFTP(BaseTests):

    @pytest.fixture(autouse=True)
    def path(self, ssh_fixture):
        self.path = UPath(ssh_fixture)
