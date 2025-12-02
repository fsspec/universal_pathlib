from pathlib import Path

import pytest

from upath import UPath

from ..cases import BaseTests


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

    @pytest.mark.parametrize(
        "target_factory",
        [
            lambda obj, name: str(obj.joinpath(name).absolute()),
            pytest.param(
                lambda obj, name: UPath(obj.absolute().joinpath(name).path),
                marks=pytest.mark.xfail(reason="webdav has no root..."),
            ),
            pytest.param(
                lambda obj, name: Path(obj.absolute().joinpath(name).path),
                marks=pytest.mark.xfail(reason="webdav has no root..."),
            ),
            lambda obj, name: obj.absolute().joinpath(name),
        ],
        ids=[
            "str_absolute",
            "plain_upath_absolute",
            "plain_path_absolute",
            "self_upath_absolute",
        ],
    )
    def test_rename_with_target_absolute(self, target_factory):
        super().test_rename_with_target_absolute(target_factory)
