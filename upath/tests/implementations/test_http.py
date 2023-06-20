import pytest  # noqa: F401
from fsspec import get_filesystem_class

from upath import UPath
from upath.implementations.http import HTTPPath

from ..cases import BaseTests
from ..utils import skip_on_windows

try:
    get_filesystem_class("http")
except ImportError:
    pytestmark = pytest.mark.skip


def test_httppath():
    path = UPath("http://example.com")
    assert isinstance(path, HTTPPath)
    assert path.exists()


def test_httpspath():
    path = UPath("https://example.com")
    assert isinstance(path, HTTPPath)
    assert path.exists()


@skip_on_windows
class TestUPathHttp(BaseTests):
    @pytest.fixture(autouse=True, scope="function")
    def path(self, http_fixture):
        self.path = UPath(http_fixture)

    def test_work_at_root(self):
        assert "folder" in (f.name for f in self.path.parent.iterdir())

    @pytest.mark.skip
    def test_mkdir(self):
        pass

    @pytest.mark.skip
    def test_mkdir_exists_ok_false(self):
        pass

    @pytest.mark.skip
    def test_mkdir_exists_ok_true(self):
        pass

    @pytest.mark.skip
    def test_mkdir_parents_true_exists_ok_true(self):
        pass

    @pytest.mark.skip
    def test_mkdir_parents_true_exists_ok_false(self):
        pass

    @pytest.mark.skip
    def test_makedirs_exist_ok_true(self):
        pass

    @pytest.mark.skip
    def test_makedirs_exist_ok_false(self):
        pass

    @pytest.mark.skip
    def test_touch_unlink(self):
        pass

    @pytest.mark.skip
    def test_write_bytes(self, pathlib_base):
        pass

    @pytest.mark.skip
    def test_write_text(self, pathlib_base):
        pass

    def test_fsspec_compat(self):
        pass

    def test_resolve(self):
        # Also tests following redirects, because the test server issues a
        # 301 redirect for `http://127.0.0.1:8080/folder` to
        # `http://127.0.0.1:8080/folder/`
        assert str(self.path.resolve()).endswith("/")

    def test_rename(self):
        with pytest.raises(NotImplementedError):
            return super().test_rename()

    def test_rename2(self):
        with pytest.raises(NotImplementedError):
            return super().test_rename()
