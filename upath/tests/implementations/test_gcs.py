import pytest

from upath import UPath
from upath.implementations.cloud import GCSPath

from ..cases import BaseTests
from ..utils import skip_on_windows


@skip_on_windows
@pytest.mark.usefixtures("path")
class TestGCSPath(BaseTests):
    SUPPORTS_EMPTY_DIRS = False

    @pytest.fixture(autouse=True, scope="function")
    def path(self, gcs_fixture):
        path, endpoint_url = gcs_fixture
        self.path = UPath(path, endpoint_url=endpoint_url)
        self.endpoint_url = endpoint_url

    def test_is_GCSPath(self):
        assert isinstance(self.path, GCSPath)

    def test_rmdir(self):
        dirname = "rmdir_test"
        mock_dir = self.path.joinpath(dirname)
        mock_dir.joinpath("test.txt").write_text("hello")
        mock_dir.fs.invalidate_cache()
        mock_dir.rmdir()
        assert not mock_dir.exists()
        with pytest.raises(NotADirectoryError):
            self.path.joinpath("file1.txt").rmdir()

    @pytest.mark.skip
    def test_makedirs_exist_ok_false(self):
        pass
