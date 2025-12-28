from pathlib import Path

import pytest

from upath import UPath
from upath.implementations.webdav import WebdavPath

from ..cases import BaseTests
from ..utils import OverrideMeta
from ..utils import extends_base
from ..utils import overrides_base


class TestUPathWebdav(BaseTests, metaclass=OverrideMeta):
    @pytest.fixture(autouse=True, scope="function")
    def path(self, webdav_fixture):
        self.path = UPath(webdav_fixture, auth=("USER", "PASSWORD"))

    @overrides_base
    def test_is_correct_class(self):
        assert isinstance(self.path, WebdavPath)

    @extends_base
    def test_storage_options_base_url(self):
        # ensure that base_url is correct
        base_url = self.path.storage_options["base_url"]
        assert base_url == self.path.fs.client.base_url

    @overrides_base
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
