import pytest

from upath import UPath
from upath.implementations.ftp import FTPPath
from upath.tests.cases import BaseTests
from upath.tests.utils import skip_on_windows

from ..utils import OverrideMeta
from ..utils import extends_base
from ..utils import overrides_base


@skip_on_windows
class TestUPathFTP(BaseTests, metaclass=OverrideMeta):

    @pytest.fixture(autouse=True)
    def path(self, ftp_server):
        self.path = UPath("", protocol="ftp", **ftp_server)
        self.prepare_file_system()

    @overrides_base
    def test_is_correct_class(self):
        assert isinstance(self.path, FTPPath)

    @extends_base
    def test_ftp_path_mtime(self, ftp_server):
        path = UPath("file1.txt", protocol="ftp", **ftp_server)
        path.touch()
        mtime = path.stat().st_mtime
        assert isinstance(mtime, float)
