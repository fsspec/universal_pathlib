import pytest  # noqa: F401

from fsspec import get_filesystem_class

from upath import UPath
from upath.implementations.http import HTTPPath

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


def test_httpiterdir(docker_http):
    path = UPath(docker_http)

    print(list(str(p) for p in path.iterdir()))
    assert path.exists()
    assert path.is_dir()
