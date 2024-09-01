import sys

import pytest

from upath import UPath

from ..cases import BaseTests


def silence_wsigdav_deprecation(cls):
    # wsgidav deprecated python 3.8 while still shipping versions supporting it?
    if sys.version_info < (3, 9):
        return pytest.mark.filterwarnings(
            "ignore"
            ":Support for Python version less than `3.9` is deprecated"
            ":DeprecationWarning"
        )(cls)
    else:
        return cls


@silence_wsigdav_deprecation
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

    def test_read_with_fsspec(self):
        # this test used to fail with fsspec<2022.5.0 because webdav was not
        # registered in fsspec. But when UPath(webdav_fixture) is called, to
        # run the BaseTests, the upath.implementations.webdav module is
        # imported, which registers the webdav implementation in fsspec.
        super().test_read_with_fsspec()
