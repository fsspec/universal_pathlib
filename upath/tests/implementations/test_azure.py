import warnings

import fsspec
import pytest

from upath import UPath
from upath.implementations.cloud import AzurePath

from ..cases import BaseTests
from ..utils import OverrideMeta
from ..utils import extends_base
from ..utils import overrides_base
from ..utils import posixify
from ..utils import skip_on_windows


@skip_on_windows
class TestAzurePath(BaseTests, metaclass=OverrideMeta):
    SUPPORTS_EMPTY_DIRS = False

    @pytest.fixture(autouse=True, scope="function")
    def path(self, azurite_credentials, azure_fixture):
        account_name, connection_string = azurite_credentials

        self.storage_options = {
            "account_name": account_name,
            "connection_string": connection_string,
        }
        self.path = UPath(azure_fixture, **self.storage_options)
        self.prepare_file_system()

    @overrides_base
    def test_is_correct_class(self):
        assert isinstance(self.path, AzurePath)

    @overrides_base
    def test_protocol(self):
        # test all valid protocols for azure...
        protocol = self.path.protocol
        protocols = ["abfs", "abfss", "adl", "az"]
        assert protocol in protocols

    @extends_base
    def test_rmdir(self):
        new_dir = self.path / "new_dir_rmdir"
        new_dir.mkdir()
        path = new_dir / "test.txt"
        path.write_text("hello")
        assert path.exists()
        new_dir.rmdir()
        assert not new_dir.exists()

        with pytest.raises(NotADirectoryError):
            (self.path / "a" / "file.txt").rmdir()

    @extends_base
    def test_broken_mkdir(self):
        path = UPath(
            "az://new-container/",
            **self.storage_options,
        )
        if path.exists():
            path.rmdir()
        path.mkdir(parents=True, exist_ok=False)

        (path / "file").write_text("foo")
        assert path.exists()


@skip_on_windows
@pytest.mark.xfail(reason="adlfs returns isdir false")
def test_copy__object_key_collides_with_dir_prefix(azurite_credentials, tmp_path):
    account_name, connection_string = azurite_credentials
    storage_options = {
        "account_name": account_name,
        "connection_string": connection_string,
    }

    az = fsspec.filesystem("az", **storage_options, use_listings_cache=False)
    container = "copy-into-collision-container"
    az.mkdir(container)
    # store more objects with same prefix
    az.pipe_file(f"{container}/src/common_prefix/file1.txt", b"1")
    az.pipe_file(f"{container}/src/common_prefix/file2.txt", b"2")
    # object under common prefix as key
    az.pipe_file(f"{container}/src/common_prefix", b"hello world")
    az.invalidate_cache()

    # make sure the sources have a collision
    assert az.isfile(f"{container}/src/common_prefix")
    assert az.isdir(f"{container}/src/common_prefix")
    assert az.isfile(f"{container}/src/common_prefix/file1.txt")
    assert az.isfile(f"{container}/src/common_prefix/file2.txt")
    # prepare source and destination
    src = UPath(f"az://{container}/src", **storage_options)
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
