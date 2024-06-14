import pytest
from fsspec import __version__ as fsspec_version
from packaging.version import Version

from upath import UPath
from upath.tests.cases import BaseTests
from upath.tests.utils import skip_on_windows


@skip_on_windows
class TestUPathSMB(BaseTests):

    @pytest.fixture(autouse=True)
    def path(self, smb_fixture):
        self.path = UPath(smb_fixture)

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
            pytest.param(
                "**/*.txt",
                marks=(
                    pytest.mark.xfail(reason="requires fsspec>=2023.9.0")
                    if Version(fsspec_version) < Version("2023.9.0")
                    else ()
                ),
            ),
        ),
    )
    def test_glob(self, pathlib_base, pattern):
        super().test_glob(pathlib_base, pattern)
