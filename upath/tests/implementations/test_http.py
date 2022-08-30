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
