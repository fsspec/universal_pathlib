import pytest

from upath import UPath
from upath.implementations.gcs import GCSPath
from upath.errors import NotDirectoryError
from ..cases import BaseTests
from ..utils import skip_on_windows


@skip_on_windows
@pytest.mark.usefixtures("path")
class TestGCSPath(BaseTests):
    @pytest.fixture(autouse=True, scope="function")
    def path(self, gcs_fixture):
        path, endpoint_url = gcs_fixture
        self.path = UPath(path, endpoint_url=endpoint_url)
        self.endpoint_url = endpoint_url

    def test_is_GCSPath(self):
        assert isinstance(self.path, GCSPath)

    def test_mkdir(self):
        new_dir = self.path.joinpath("new_dir")
        new_dir.joinpath("test.txt").touch()
        assert new_dir.exists()

    def test_rmdir(self, local_testdir):
        dirname = "rmdir_test"
        mock_dir = self.path.joinpath(dirname)
        mock_dir.joinpath("test.txt").write_text("hello")
        mock_dir.fs.invalidate_cache()
        mock_dir.rmdir()
        assert not mock_dir.exists()
        with pytest.raises(NotDirectoryError):
            self.path.joinpath("file1.txt").rmdir()

    def test_fsspec_compat(self):
        fs = self.path.fs
        content = b"a,b,c\n1,2,3\n4,5,6"

        if not fs.exists("gs://tmp"):
            fs.mkdir("gs://tmp")

        p1 = "gs://tmp/output1.csv"
        upath1 = UPath(p1, endpoint_url=self.endpoint_url)
        upath1.write_bytes(content)
        with fs.open(p1) as f:
            assert f.read() == content
        upath1.unlink()

        # write with fsspec, read with upath
        p2 = "gs://tmp/output2.csv"
        with fs.open(p2, "wb") as f:
            f.write(content)
        upath2 = UPath(p2, endpoint_url=self.endpoint_url)
        assert upath2.read_bytes() == content
        upath2.unlink()
