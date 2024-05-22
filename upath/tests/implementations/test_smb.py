import pytest

from upath import UPath
from upath.tests.cases import BaseTests


class TestUPathSMB(BaseTests):

    @pytest.fixture(autouse=True)
    def path(self, smb_fixture):
        self.path = UPath(smb_fixture)
