import fsspec
import pytest

from upath import UPath
from upath.implementations.cloud import GCSPath

from ..cases import BaseTests
from ..utils import OverrideMeta
from ..utils import extends_base
from ..utils import overrides_base
from ..utils import skip_on_windows


@skip_on_windows
class TestGCSPath(BaseTests, metaclass=OverrideMeta):
    SUPPORTS_EMPTY_DIRS = False

    @pytest.fixture(autouse=True, scope="function")
    def path(self, gcs_fixture):
        path, endpoint_url = gcs_fixture
        self.path = UPath(path, endpoint_url=endpoint_url, token="anon")

    @overrides_base
    def test_is_correct_class(self):
        assert isinstance(self.path, GCSPath)

    @extends_base
    def test_rmdir(self):
        dirname = "rmdir_test"
        mock_dir = self.path.joinpath(dirname)
        mock_dir.joinpath("test.txt").write_text("hello")
        mock_dir.fs.invalidate_cache()
        mock_dir.rmdir()
        assert not mock_dir.exists()
        with pytest.raises(NotADirectoryError):
            self.path.joinpath("file1.txt").rmdir()


@skip_on_windows
def test_mkdir_in_empty_bucket(docker_gcs):
    fs = fsspec.filesystem("gcs", endpoint_url=docker_gcs, token="anon")
    fs.mkdir("my-fresh-bucket")
    assert "my-fresh-bucket/" in fs.buckets
    fs.invalidate_cache()
    del fs

    UPath(
        "gs://my-fresh-bucket/some-dir/another-dir/file",
        endpoint_url=docker_gcs,
        token="anon",
    ).parent.mkdir(parents=True, exist_ok=True)
