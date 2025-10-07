import pytest  # noqa: F401
from fsspec import __version__ as fsspec_version
from fsspec import get_filesystem_class
from packaging.version import Version

from upath import UPath
from upath.implementations.http import HTTPPath

from ..cases import BaseTests
from ..utils import skip_on_windows
from ..utils import xfail_if_no_ssl_connection
from ..utils import xfail_if_version

try:
    get_filesystem_class("http")
except ImportError:
    pytestmark = pytest.mark.skip


def test_httppath():
    path = UPath("http://example.com")
    assert isinstance(path, HTTPPath)
    assert path.exists()


@xfail_if_no_ssl_connection
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

    @pytest.mark.parametrize(
        "pattern",
        (
            "*.txt",
            pytest.param(
                "*",
                marks=xfail_if_version(
                    "fsspec",
                    gt="2023.10.0",
                    lt="2024.5.0",
                    reason="requires fsspec>=2024.5.0",
                ),
            ),
            pytest.param(
                "**/*.txt",
                marks=(
                    pytest.mark.xfail(reason="requires fsspec>=2023.9.0")
                    if Version(fsspec_version) < Version("2023.9.0")
                    else ()
                ),
            ),
        ),
    )
    def test_glob(self, pathlib_base, pattern):
        super().test_glob(pathlib_base, pattern)

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
    def test_touch(self):
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

    @xfail_if_version("fsspec", lt="2024.2.0", reason="requires fsspec>=2024.2.0")
    def test_stat_dir_st_mode(self):
        super().test_stat_dir_st_mode()

    def test_info(self):
        p0 = self.path.joinpath("file1.txt")
        p1 = self.path.joinpath("folder1")

        assert p0.info.exists() is True
        assert p0.info.is_file() is True
        assert p0.info.is_dir() is False
        assert p0.info.is_symlink() is False
        assert p1.info.exists() is True
        assert (
            p1.info.is_file() is True
        )  # Weird quirk of how directories work in http fsspec
        assert p1.info.is_dir() is True
        assert p1.info.is_symlink() is False

    @pytest.mark.skip(reason="HttpPath does not support unlink")
    def test_move_local(self, tmp_path):
        pass

    @pytest.mark.skip(reason="HttpPath does not support unlink")
    def test_move_into_local(self, tmp_path):
        pass

    @pytest.mark.skip(reason="HttpPath does not support unlink")
    def test_move_memory(self, clear_fsspec_memory_cache):
        pass

    @pytest.mark.skip(reason="HttpPath does not support unlink")
    def test_move_into_memory(self, clear_fsspec_memory_cache):
        pass


@pytest.mark.parametrize(
    "args,parts",
    [
        (("http://example.com/"), ("http://example.com/", "")),
        (("http://example.com//"), ("http://example.com/", "", "")),
        (("http://example.com///"), ("http://example.com/", "", "", "")),
        (("http://example.com/a"), ("http://example.com/", "a")),
        (("http://example.com/a/"), ("http://example.com/", "a", "")),
        (("http://example.com/a/b"), ("http://example.com/", "a", "b")),
        (("http://example.com/a//b"), ("http://example.com/", "a", "", "b")),
        (("http://example.com/a//b/"), ("http://example.com/", "a", "", "b", "")),
    ],
)
def test_empty_parts(args, parts):
    pth = UPath(args)
    pth_parts = pth.parts
    assert pth_parts == parts


def test_query_parameters_passthrough():
    pth = UPath("http://example.com/?a=1&b=2")
    assert pth.parts == ("http://example.com/", "?a=1&b=2")


@pytest.mark.parametrize(
    "base,rel,expected",
    [
        (
            "http://www.example.com/a/b/index.html",
            "image.png?version=1",
            "http://www.example.com/a/b/image.png?version=1",
        ),
        (
            "http://www.example.com/a/b/index.html",
            "../image.png",
            "http://www.example.com/a/image.png",
        ),
        (
            "http://www.example.com/a/b/index.html",
            "/image.png",
            "http://www.example.com/image.png",
        ),
        (
            "http://www.example.com/a/b/index.html",
            "sftp://other.com/image.png",
            "sftp://other.com/image.png",
        ),
        (
            "http://www.example.com/a/b/index.html",
            "//other.com/image.png",
            "http://other.com/image.png",
        ),
    ],
)
def test_joinuri_behavior(base, rel, expected):
    p0 = UPath(base)
    pr = p0.joinuri(rel)
    pe = UPath(expected)
    assert pr == pe


NORMALIZATIONS = (
    ("unnormalized", "normalized"),
    (
        # Expected normalization results according to curl
        ("http://example.com", "http://example.com/"),
        ("http://example.com/", "http://example.com/"),
        ("http://example.com/a", "http://example.com/a"),
        ("http://example.com//a", "http://example.com//a"),
        ("http://example.com///a", "http://example.com///a"),
        ("http://example.com////a", "http://example.com////a"),
        ("http://example.com/a/.", "http://example.com/a/"),
        ("http://example.com/a/./", "http://example.com/a/"),
        ("http://example.com/a/./b", "http://example.com/a/b"),
        ("http://example.com/a/.//", "http://example.com/a//"),
        ("http://example.com/a/.//b", "http://example.com/a//b"),
        ("http://example.com/a//.", "http://example.com/a//"),
        ("http://example.com/a//./", "http://example.com/a//"),
        ("http://example.com/a//./b", "http://example.com/a//b"),
        ("http://example.com/a//.//", "http://example.com/a///"),
        ("http://example.com/a//.//b", "http://example.com/a///b"),
        ("http://example.com/a/..", "http://example.com/"),
        ("http://example.com/a/../", "http://example.com/"),
        ("http://example.com/a/../.", "http://example.com/"),
        ("http://example.com/a/../..", "http://example.com/"),
        ("http://example.com/a/../../", "http://example.com/"),
        ("http://example.com/a/../..//", "http://example.com//"),
        ("http://example.com/a/..//", "http://example.com//"),
        ("http://example.com/a/..//.", "http://example.com//"),
        ("http://example.com/a/..//..", "http://example.com/"),
        ("http://example.com/a/../b", "http://example.com/b"),
        ("http://example.com/a/..//b", "http://example.com//b"),
        ("http://example.com/a//..", "http://example.com/a/"),
        ("http://example.com/a//../", "http://example.com/a/"),
        ("http://example.com/a//../.", "http://example.com/a/"),
        ("http://example.com/a//../..", "http://example.com/"),
        ("http://example.com/a//../../", "http://example.com/"),
        ("http://example.com/a//../..//", "http://example.com//"),
        ("http://example.com/a//..//..", "http://example.com/a/"),
        ("http://example.com/a//../b", "http://example.com/a/b"),
        ("http://example.com/a//..//", "http://example.com/a//"),
        ("http://example.com/a//..//.", "http://example.com/a//"),
        ("http://example.com/a//..//b", "http://example.com/a//b"),
    ),
)


@pytest.mark.parametrize(*NORMALIZATIONS)
def test_normalize(unnormalized, normalized):
    expected = HTTPPath(normalized)
    pth = HTTPPath(unnormalized)
    assert expected.protocol in {"http", "https"}
    assert pth.protocol in {"http", "https"}

    # Normalise only, do not attempt to follow redirects for http:// paths here
    result = pth.resolve(strict=True, follow_redirects=False)

    str_expected = str(expected)
    str_result = str(result)
    assert expected == result
    assert str_expected == str_result
