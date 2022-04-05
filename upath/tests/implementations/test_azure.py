import pytest
import sys

from upath import UPath
from upath.implementations.azure import AzurePath
from upath.errors import NotDirectoryError
from upath.tests.cases import BaseTests


URL = "http://127.0.0.1:10000"
ACCOUNT_NAME = "devstoreaccount1"
KEY = "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw=="  # NOQA
CONN_STR = f"DefaultEndpointsProtocol=http;AccountName={ACCOUNT_NAME};AccountKey={KEY};BlobEndpoint={URL}/{ACCOUNT_NAME};"  # NOQA


@pytest.mark.skipif(sys.platform.startswith("win"), reason="Windows bad")
@pytest.mark.usefixtures("path")
class TestAzurePath(BaseTests):
    @pytest.fixture(autouse=True, scope="function")
    def path(self, azurite_storage):
        path = "az://data/root"
        self.storage_options = {
            "account_name": azurite_storage.account_name,
            "connection_string": CONN_STR,
        }
        self.path = UPath(f"{path}", **self.storage_options)

    def test_is_AzurePath(self):
        assert isinstance(self.path, AzurePath)

    def test_mkdir(self):
        new_dir = self.path / "new_dir"
        new_dir.mkdir()
        (new_dir / "test.txt").touch()
        assert new_dir.exists()

    @pytest.mark.parametrize(
        "pattern, expected",
        [
            ("b/*", 1),
            ("*/file.txt", 2),
            ("*/file[0-9].txt", 5),
            ("**/*.txt", 9),
            ("**/*.jpg", 0),
        ],
    )
    def test_glob(self, pattern, expected):

        paths = list(self.path.glob(pattern))
        assert len(paths) == expected

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

    def test_fsspec_compat(self):
        fs = self.path.fs
        scheme = self.path._url.scheme
        content = b"a,b,c\n1,2,3\n4,5,6"
        p1 = f"{scheme}:///data/root/output1.csv"
        upath1 = UPath(p1, **self.storage_options)
        upath1.write_bytes(content)
        with fs.open(p1) as f:
            assert f.read() == content

        upath1.unlink()

        p2 = f"{scheme}:///data/root/output2.csv"
        with fs.open(p2, "wb") as f:
            f.write(content)

        upath2 = UPath(p2, **self.storage_options)
        assert upath2.read_bytes() == content
        upath2.unlink()

    def test_child_path(self):
        path_a = UPath(f"{self.path}/folder", **self.storage_options)
        path_b = self.path / "folder"
        assert str(path_a) == str(path_b)
        assert path_a._root == path_b._root
        assert path_a._drv == path_b._drv
        assert path_a._parts == path_b._parts
        assert path_a._url == path_b._url

    def test_read_bytes(self):
        path = self.path / "file1.txt"
        assert path.read_bytes() == b"0123456789"

    def test_read_text(self):
        path = self.path / "file1.txt"
        assert path.read_text() == "0123456789"

    def test_iterdir(self):
        assert next(self.path.parent.iterdir()).exists()
