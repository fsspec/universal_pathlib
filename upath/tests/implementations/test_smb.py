import pytest

from upath import UPath

from ..cases import BaseTests
from ..utils import OverrideMeta
from ..utils import overrides_base
from ..utils import skip_on_windows


@skip_on_windows
class TestUPathSMB(BaseTests, metaclass=OverrideMeta):

    @pytest.fixture(autouse=True)
    def path(self, smb_fixture):
        self.path = UPath(smb_fixture)

    @overrides_base
    def test_is_correct_class(self):
        from upath.implementations.smb import SMBPath

        assert isinstance(self.path, SMBPath)

    @overrides_base
    @pytest.mark.parametrize(
        "pattern",
        (
            "*.txt",
            pytest.param(
                "*",
                marks=pytest.mark.xfail(
                    reason="SMBFileSystem.info appends '/' to dirs"
                ),
            ),
            "**/*.txt",
        ),
    )
    def test_glob(self, pathlib_base, pattern):
        super().test_glob(pathlib_base, pattern)
