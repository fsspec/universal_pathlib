import pytest  # noqa: F401

from upath import UPath
from upath.implementations.http import HTTPPath


def test_httppath():
    path = UPath("http://example.com")
    assert isinstance(path, HTTPPath)
    assert path.exists()
