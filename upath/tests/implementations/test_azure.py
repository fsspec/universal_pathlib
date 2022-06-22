import pytest
from upath import UPath
from upath.errors import NotDirectoryError
from upath.implementations.cloud import AzurePath

from ..cases import BaseTests
from ..utils import skip_on_windows


@skip_on_windows
@pytest.mark.usefixtures("path")
class TestAzurePath(BaseTests):
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

    def test_mkdir(self):
        new_dir = self.path / "new_dir"
        new_dir.mkdir()
        (new_dir / "test.txt").touch()
        assert new_dir.exists()

    def test_rmdir(self):
        new_dir = self.path / "new_dir"
        new_dir.mkdir()
        path = new_dir / "test.txt"
        path.write_text("hello")
        assert path.exists()
        new_dir.fs.invalidate_cache()
        new_dir.rmdir()
        assert not new_dir.exists()

        with pytest.raises(NotDirectoryError):
            (self.path / "a" / "file.txt").rmdir()
