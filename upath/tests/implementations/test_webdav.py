import pytest  # noqa: F401

from upath import UPath
from ..cases import BaseTests


class TestUPathWebdav(BaseTests):
    @pytest.fixture(autouse=True, scope="function")
    def path(self, webdav_fixture):
        self.path = UPath(webdav_fixture, auth=("USER", "PASSWORD"))

    def test_fsspec_compat(self):
        pass
