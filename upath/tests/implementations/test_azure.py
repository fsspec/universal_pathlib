import pytest

from upath import UPath
from upath.implementations.cloud import AzurePath

from ..cases import BaseTests
from ..utils import skip_on_windows


@skip_on_windows
@pytest.mark.usefixtures("path")
class TestAzurePath(BaseTests):
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

    def test_is_AzurePath(self):
        assert isinstance(self.path, AzurePath)

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

    @pytest.mark.skip
    def test_makedirs_exist_ok_false(self):
        pass

    def test_rglob(self, pathlib_base):
        return super().test_rglob(pathlib_base)

    def test_protocol(self):
        # test all valid protocols for azure...
        protocol = self.path.protocol
        assert protocol in ["abfs", "abfss", "adl", "az"]
