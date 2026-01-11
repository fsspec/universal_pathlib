import warnings

import fsspec
import pytest

from upath import UPath
from upath.implementations.cloud import GCSPath

from ..cases import BaseTests
from ..utils import OverrideMeta
from ..utils import extends_base
from ..utils import overrides_base
from ..utils import posixify
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


@skip_on_windows
@pytest.mark.xfail(reason="gcsfs returns isdir false")
def test_copy__object_key_collides_with_dir_prefix(docker_gcs, tmp_path):
    gcs = fsspec.filesystem(
        "gcs",
        endpoint_url=docker_gcs,
        token="anon",
        use_listings_cache=False,
    )
    bucket = "copy_into_collision_bucket"
    gcs.mkdir(bucket)
    # gcs.mkdir(bucket + "/src" + "/common_prefix/")
    # object under common prefix as key
    gcs.pipe_file(f"{bucket}/src/common_prefix", b"hello world")
    # store more objects with same prefix
    gcs.pipe_file(f"{bucket}/src/common_prefix/file1.txt", b"1")
    gcs.pipe_file(f"{bucket}/src/common_prefix/file2.txt", b"2")
    gcs.invalidate_cache()

    # make sure the sources have a collision
    assert gcs.isfile(f"{bucket}/src/common_prefix")
    assert gcs.isdir(f"{bucket}/src/common_prefix")  # BROKEN in gcsfs
    assert gcs.isfile(f"{bucket}/src/common_prefix/file1.txt")
    assert gcs.isfile(f"{bucket}/src/common_prefix/file2.txt")
    # prepare source and destination
    src = UPath(f"gs://{bucket}/src", endpoint_url=docker_gcs, token="anon")
    dst = UPath(tmp_path)

    def on_collision_rename_file(src, dst):
        warnings.warn(
            f"{src!s} collides with prefix. Renaming target file object to {dst!s}",
            UserWarning,
            stacklevel=3,
        )
        return (
            dst.with_suffix(dst.suffix + ".COLLISION"),
            dst,
        )

    # perform copy
    src.copy_into(dst, on_name_collision=on_collision_rename_file)

    # check results
    dst_files = sorted(posixify(x.relative_to(tmp_path)) for x in dst.glob("**/*"))
    assert dst_files == [
        "src",
        "src/common_prefix",
        "src/common_prefix.COLLISION",
        "src/common_prefix/file1.txt",
        "src/common_prefix/file2.txt",
    ]
