import pytest
import sys

from upath import UPath
from upath.implementations.gcs import GCSPath
from upath.errors import NotDirectoryError
from upath.tests.cases import BaseTests


@pytest.mark.skipif(sys.platform.startswith("win"), reason="Windows bad")
@pytest.mark.usefixtures("path")
class TestGCSPath(BaseTests):
    @pytest.fixture(autouse=True, scope="function")
    def path(self, local_testdir, gcs):
        scheme = "gs:/"
        self.path = UPath(f"{scheme}{local_testdir}", endpoint_url=gcs)
        self.endpoint_url = gcs

    def test_is_GCSPath(self):
        assert isinstance(self.path, GCSPath)

    def test_mkdir(self):
        new_dir = self.path.joinpath("new_dir")
        new_dir.joinpath("test.txt").touch()
        assert new_dir.exists()

    def test_glob(self, pathlib_base):
        mock_glob = list(self.path.glob("**.txt"))
        path_glob = list(pathlib_base.glob("**/*.txt"))

        assert len(mock_glob) == len(path_glob)
        assert all(
            map(lambda m: m.path in [str(p)[4:] for p in path_glob], mock_glob)
        )

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
        scheme = self.path._url.scheme
        content = b"a,b,c\n1,2,3\n4,5,6"

        p1 = f"{scheme}:///tmp/output1.csv"
        upath1 = UPath(p1, endpoint_url=self.endpoint_url)
        upath1.write_bytes(content)
        with fs.open(p1) as f:
            assert f.read() == content
        upath1.unlink()

        # write with fsspec, read with upath
        p2 = f"{scheme}:///tmp/output2.csv"
        with fs.open(p2, "wb") as f:
            f.write(content)
        upath2 = UPath(p2, endpoint_url=self.endpoint_url)
        assert upath2.read_bytes() == content
        upath2.unlink()
