"""Tests for fsid-based path equivalence."""

import pytest

from upath import UPath


# --- __eq__ tests ---


def test_eq_with_fsid_local(tmp_path):
    """Local paths with different storage_options should be equal."""
    p1 = UPath(tmp_path / "test.txt")
    p2 = UPath(tmp_path / "test.txt", auto_mkdir=True)
    assert p1 == p2


def test_eq_with_fsid_http():
    """HTTP paths with different storage_options should be equal."""
    p1 = UPath("http://example.com/file.txt")
    p2 = UPath("http://example.com/file.txt", block_size=1024)
    assert p1 == p2


def test_eq_http_https_different_protocol():
    """HTTP and HTTPS are different protocols, so paths are not equal."""
    p1 = UPath("http://example.com/file.txt")
    p2 = UPath("https://example.com/file.txt")
    assert p1 != p2


def test_eq_different_filesystem():
    """Paths on different filesystems should not be equal."""
    p1 = UPath("/tmp/file.txt")
    p2 = UPath("memory:///tmp/file.txt")
    assert p1 != p2


def test_eq_s3_same_endpoint():
    """S3 paths with same endpoint but different auth should be equal."""
    p1 = UPath("s3://bucket/key")
    p2 = UPath("s3://bucket/key", anon=True)
    assert p1 == p2


def test_eq_s3_different_endpoint():
    """S3 paths with different endpoints should not be equal."""
    p1 = UPath("s3://bucket/key")
    p2 = UPath("s3://bucket/key", endpoint_url="http://localhost:9000")
    assert p1 != p2


# --- relative_to tests ---


def test_relative_to_with_fsid(tmp_path):
    """relative_to should work when fsids match."""
    p1 = UPath(tmp_path / "dir" / "file.txt")
    p2 = UPath(tmp_path / "dir", auto_mkdir=True)
    rel = p1.relative_to(p2)
    assert str(rel) == "file.txt"


def test_relative_to_different_fsid():
    """relative_to should raise when fsids differ."""
    p1 = UPath("s3://bucket/dir/file.txt")
    p2 = UPath("s3://bucket/dir", endpoint_url="http://localhost:9000")
    with pytest.raises(ValueError, match="incompatible filesystems"):
        p1.relative_to(p2)


# --- is_relative_to tests ---


def test_is_relative_to_with_fsid(tmp_path):
    """is_relative_to should return True when fsids match."""
    p1 = UPath(tmp_path / "dir" / "file.txt")
    p2 = UPath(tmp_path / "dir", auto_mkdir=True)
    assert p1.is_relative_to(p2)


def test_is_relative_to_different_fsid():
    """is_relative_to should return False when fsids differ."""
    p1 = UPath("s3://bucket/dir/file.txt")
    p2 = UPath("s3://bucket/dir", endpoint_url="http://localhost:9000")
    assert not p1.is_relative_to(p2)


# --- _fallback_fsid audit tests ---
# These tests verify that our fallback fsid computation matches
# the native fsid implementations in fsspec filesystems.


def test_fallback_matches_local_filesystem():
    """Verify _fallback_fsid matches LocalFileSystem.fsid."""
    from upath._fsid import _fallback_fsid

    p = UPath("/tmp/test.txt")
    native_fsid = p.fs.fsid
    fallback_fsid = _fallback_fsid(p.protocol, p.storage_options)
    assert native_fsid == fallback_fsid == "local"


def test_fallback_matches_http_filesystem():
    """Verify _fallback_fsid matches HTTPFileSystem.fsid."""
    from upath._fsid import _fallback_fsid

    for url in ["http://example.com/file.txt", "https://example.com/file.txt"]:
        p = UPath(url)
        native_fsid = p.fs.fsid
        fallback_fsid = _fallback_fsid(p.protocol, p.storage_options)
        assert native_fsid == fallback_fsid == "http"


def test_fsid_consistency_cached_vs_uncached(tmp_path):
    """Verify fsid is consistent whether filesystem is cached or not."""
    # Create two paths - check fsid before and after fs access
    p1 = UPath(tmp_path / "test.txt")
    p2 = UPath(tmp_path / "test.txt", auto_mkdir=True)

    # Before any fs access (uses fallback)
    fsid1_before = p1.fsid
    fsid2_before = p2.fsid

    # Access fs on p1 only (p1 now uses cached fs.fsid)
    _ = p1.fs
    fsid1_after = p1.fsid
    fsid2_still_fallback = p2.fsid

    # All should be equal
    assert fsid1_before == fsid2_before == fsid1_after == fsid2_still_fallback == "local"


def test_fallback_uses_global_config():
    """Verify _fallback_fsid incorporates fsspec global config."""
    from fsspec.config import conf as fsspec_conf

    from upath._fsid import _fallback_fsid

    # Before setting config - default AWS
    assert _fallback_fsid("s3", {}) == "s3_aws"

    # Set global config
    fsspec_conf["s3"] = {"endpoint_url": "http://minio.local:9000"}
    try:
        # Should now use the global config endpoint
        fsid_with_config = _fallback_fsid("s3", {})
        assert fsid_with_config != "s3_aws"
        assert fsid_with_config.startswith("s3_")

        # Explicit storage_options should override global config
        assert _fallback_fsid("s3", {"endpoint_url": "https://s3.amazonaws.com"}) == "s3_aws"
    finally:
        # Clean up
        del fsspec_conf["s3"]


def test_fallback_ignores_auth_options():
    """Verify auth options don't affect fsid."""
    from upath._fsid import _fallback_fsid

    base = _fallback_fsid("s3", {})
    with_anon = _fallback_fsid("s3", {"anon": True})
    with_key = _fallback_fsid("s3", {"key": "xxx", "secret": "yyy"})

    assert base == with_anon == with_key == "s3_aws"


def test_fallback_respects_identity_options():
    """Verify identity-relevant options produce different fsids."""
    from upath._fsid import _fallback_fsid

    # S3: different endpoints = different fsid
    aws = _fallback_fsid("s3", {})
    minio = _fallback_fsid("s3", {"endpoint_url": "http://localhost:9000"})
    assert aws != minio

    # SFTP: different hosts = different fsid
    host1 = _fallback_fsid("sftp", {"host": "server1.com"})
    host2 = _fallback_fsid("sftp", {"host": "server2.com"})
    assert host1 != host2

    # SFTP: different ports = different fsid
    port22 = _fallback_fsid("sftp", {"host": "server.com", "port": 22})
    port2222 = _fallback_fsid("sftp", {"host": "server.com", "port": 2222})
    assert port22 != port2222

    # Azure: different accounts = different fsid
    acc1 = _fallback_fsid("abfs", {"account_name": "storage1"})
    acc2 = _fallback_fsid("abfs", {"account_name": "storage2"})
    assert acc1 != acc2
