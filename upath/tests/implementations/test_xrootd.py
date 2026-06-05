import pytest

from upath import UPath
from upath.implementations.xrootd import XRootDPath

from ..cases import BaseTests
from ..utils import OverrideMeta
from ..utils import overrides_base


class TestUPathXRootD(BaseTests, metaclass=OverrideMeta):
    @pytest.fixture(autouse=True, scope="function")
    def path(self, xrootd_fixture):
        self.path = UPath(xrootd_fixture)

    @overrides_base
    def test_is_correct_class(self):
        assert isinstance(self.path, XRootDPath)
