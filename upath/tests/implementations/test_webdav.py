import pytest  # noqa: F401

from upath import UPath

from ..cases import BaseTests
from ..utils import xfail_if_version


class TestUPathWebdav(BaseTests):
    @pytest.fixture(autouse=True, scope="function")
    def path(self, webdav_fixture):
        self.path = UPath(webdav_fixture, auth=("USER", "PASSWORD"))

    def test_fsspec_compat(self):
        pass

    def test_storage_options(self):
        # we need to add base_url to storage options for webdav filesystems,
        # to be able to serialize the http protocol to string...
        storage_options = self.path.storage_options
        base_url = storage_options["base_url"]
        assert storage_options == self.path.fs.storage_options
        assert base_url == self.path.fs.client.base_url

    @xfail_if_version("fsspec", lt="2022.5.0", reason="requires fsspec>=2022.5.0")
    def test_read_with_fsspec(self):
        super().test_read_with_fsspec()
