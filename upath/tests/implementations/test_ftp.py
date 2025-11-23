import pytest

from upath import UPath
from upath.tests.cases import BaseTests
from upath.tests.utils import skip_on_windows


@skip_on_windows
class TestUPathFTP(BaseTests):

    @pytest.fixture(autouse=True)
    def path(self, ftp_server):
        self.path = UPath("", protocol="ftp", **ftp_server)
        self.prepare_file_system()


def test_ftp_path_mtime(ftp_server):
    path = UPath("file1.txt", protocol="ftp", **ftp_server)
    path.touch()
    mtime = path.stat().st_mtime
    assert isinstance(mtime, float)
