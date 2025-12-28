import pytest  # noqa: F401
from fsspec import get_filesystem_class

from upath import UPath
from upath.implementations.http import HTTPPath

from ..cases import JoinablePathTests
from ..cases import NonWritablePathTests
from ..cases import ReadablePathTests
from ..utils import OverrideMeta
from ..utils import extends_base
from ..utils import overrides_base
from ..utils import skip_on_windows
from ..utils import xfail_if_no_ssl_connection

try:
    get_filesystem_class("http")
except ImportError:
    pytestmark = pytest.mark.skip


@pytest.fixture
def internet_connection():
    import requests

    try:
        requests.get("http://example.com")
    except requests.exceptions.ConnectionError:
        pytest.xfail(reason="No internet connection")
    else:
        yield


def test_httppath(internet_connection):
    path = UPath("http://example.com")
    assert isinstance(path, HTTPPath)
    assert path.exists()


@xfail_if_no_ssl_connection
def test_httpspath(internet_connection):
    path = UPath("https://example.com")
    assert isinstance(path, HTTPPath)
    assert path.exists()


@skip_on_windows
class TestUPathHttp(
    JoinablePathTests,
    ReadablePathTests,
    NonWritablePathTests,
    metaclass=OverrideMeta,
):
    @pytest.fixture(autouse=True, scope="function")
    def path(self, http_fixture):
        self.path = UPath(http_fixture)

    @overrides_base
    def test_is_correct_class(self):
        assert isinstance(self.path, HTTPPath)

    @extends_base
    def test_work_at_root(self):
        assert "folder" in (f.name for f in self.path.parent.iterdir())

    @extends_base
    def test_resolve(self):
        # Also tests following redirects, because the test server issues a
        # 301 redirect for `http://127.0.0.1:8080/folder` to
        # `http://127.0.0.1:8080/folder/`
        assert str(self.path.resolve()).endswith("/")

    @overrides_base
    def test_info(self):
        # HTTPPath folders are files too

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
