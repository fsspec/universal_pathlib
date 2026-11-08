"""pure (filesystem independent) tests for CloudPath subclasses"""

import pytest

from upath import UnsupportedOperation
from upath import UPath
from upath.implementations.cloud import CloudPath


@pytest.mark.parametrize(
    "urlpath,key",
    [
        # bucket root
        ("s3://bucket", ""),
        ("s3://bucket/", ""),
        ("gs://bucket", ""),
        ("az://container/", ""),
        # object keys
        ("s3://bucket/a", "a"),
        ("s3://bucket/a/b/c.txt", "a/b/c.txt"),
        ("s3a://bucket/a/b", "a/b"),
        ("gs://bucket-name/A/B/C/filename.tar.gz", "A/B/C/filename.tar.gz"),
        ("gcs://bucket/a/b", "a/b"),
        ("az://container/a/b", "a/b"),
        ("abfs://container/a/b", "a/b"),
        ("abfss://container@account.dfs.core.windows.net/a/b", "a/b"),
        # trailing slashes are not preserved (same as .path)
        ("s3://bucket/a/", "a"),
        ("gs://bucket/a/b//", "a/b"),
        # empty path segments are part of the key
        ("s3://bucket//key", "/key"),
        ("s3://bucket/a//b", "a//b"),
        ("gs://bucket//key", "/key"),
        ("az://container//key", "/key"),
    ],
)
def test_cloudpath_key(urlpath, key):
    pth = UPath(urlpath)
    assert isinstance(pth, CloudPath)
    assert pth.key == key
    assert pth.anchor + pth.key == pth.path


@pytest.mark.parametrize("protocol", ["s3", "gs", "az"])
def test_cloudpath_key_derived_paths(protocol):
    root = UPath(f"{protocol}://bucket")
    pth = root / "a" / "b.txt"
    assert pth.key == "a/b.txt"
    assert pth.parent.key == "a"
    assert pth.parent.parent.key == ""
    assert pth.with_name("c.txt").key == "a/c.txt"
    assert UPath(pth).key == "a/b.txt"


@pytest.mark.parametrize("protocol", ["s3", "gs", "az"])
def test_cloudpath_key_bucket_roundtrip(protocol):
    pth = UPath(f"{protocol}://bucket/a/b/c.txt")
    assert UPath(pth.key, protocol=protocol, bucket=pth.drive) == pth


def test_cloudpath_key_relative_path_unsupported():
    rel = UPath("s3://bucket/a/b").relative_to(UPath("s3://bucket/"))
    assert str(rel) == "a/b"
    with pytest.raises(UnsupportedOperation):
        rel.key


def test_hfpath_key_unsupported():
    pth = UPath("hf://datasets/user/repo/data/file.csv")
    with pytest.raises(UnsupportedOperation, match="HfPath.key is unsupported"):
        pth.key


def test_key_not_available_on_non_cloud_paths():
    assert not hasattr(UPath("memory:///a/b"), "key")
