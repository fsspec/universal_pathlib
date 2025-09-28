"""Tests for relative path functionality."""

import os
import pickle
import re
import tempfile
from pathlib import Path

import pytest

from upath import UPath


@pytest.mark.parametrize(
    "protocol,storage_options,path,base",
    [
        ("memory", {}, "memory:///foo/bar/baz.txt", "memory:///foo"),
        ("s3", {"anon": True}, "s3://bucket/foo/bar/baz.txt", "s3://bucket/foo"),
        ("gcs", {"token": "anon"}, "gcs://bucket/foo/bar/baz.txt", "gcs://bucket/foo"),
        ("http", {"something": 1}, "http://host/foo/bar/baz.txt", "http://host/foo"),
        (
            "https",
            {},
            "https://host/foo/bar/baz.txt",
            "https://host/",
        ),
    ],
)
def test_protocol_storage_options_fs_preserved(protocol, storage_options, path, base):
    """Test that protocol and storage_options are preserved in relative paths."""
    p = UPath(path, protocol=protocol, **storage_options)
    root = UPath(base, protocol=protocol, **storage_options)
    rel = p.relative_to(root)

    assert rel.protocol == protocol
    assert dict(**rel.storage_options) == storage_options
    assert isinstance(rel.fs, type(p.fs))


@pytest.mark.parametrize(
    "protocol,path,base",
    [
        ("s3", "s3://bucket/foo/bar/baz.txt", "s3://bucket/foo"),
        ("gcs", "gcs://bucket/foo/bar/baz.txt", "gcs://bucket/foo"),
        ("ftp", "ftp://user:pass@host/foo/bar/baz.txt", "ftp://user:pass@host/foo"),
        ("http", "http://host/foo/bar/baz.txt", "http://host/foo"),
        ("https", "https://host/foo/bar/baz.txt", "https://host/foo"),
        ("memory", "memory:///foo/bar/baz.txt", "memory:///foo"),
    ],
)
def test_relative_urlpath_raises_without_cwd(protocol, path, base):
    rel = UPath(path, protocol=protocol).relative_to(UPath(base, protocol=protocol))
    with pytest.raises(
        NotImplementedError,
        match=re.escape(f"{type(rel).__name__}.cwd() is unsupported"),
    ):
        rel.cwd()
    with pytest.raises(
        NotImplementedError,
        match=re.escape(
            f"fsspec paths can not be relative and"
            f" {type(rel).__name__}.cwd() is unsupported"
        ),
    ):
        _ = rel.path


@pytest.mark.parametrize(
    "pth,base,rel",
    [
        ("/foo/bar/baz.txt", "/foo", "bar/baz.txt"),
        ("/foo/bar/baz/qux.txt", "/foo/bar", "baz/qux.txt"),
        ("/foo/bar/baz/qux.txt", "/foo/bar/baz", "qux.txt"),
        ("/foo/bar/baz", "/foo/bar/baz", "."),
    ],
)
@pytest.mark.parametrize(
    "protocol",
    [
        "memory",
        "file",
        "",
    ],
)
def test_basic_relative_path_creation(protocol, pth, base, rel):
    rel_pth = UPath(pth, protocol=protocol).relative_to(UPath(base, protocol=protocol))

    assert not rel_pth.is_absolute()
    assert rel_pth.as_posix() == rel


def test_relative_path_validation():
    """Test validation of relative_to arguments."""
    p = UPath("memory:///foo/bar")

    # Different protocols should fail
    with pytest.raises(ValueError, match="incompatible protocols"):
        p.relative_to(UPath("s3://bucket"))

    # Different storage options should fail
    with pytest.raises(ValueError, match="incompatible storage_options"):
        UPath("s3://bucket/file", anon=True).relative_to(
            UPath("s3://bucket", anon=False)
        )


def test_path_not_in_subpath():
    """Test relative_to with paths that don't have a parent-child relationship."""
    p = UPath("memory:///foo/bar")
    other = UPath("memory:///baz")

    with pytest.raises(ValueError, match="is not in the subpath of"):
        p.relative_to(other)


def test_filesystem_operations_fail_without_cwd():
    """Test that filesystem operations fail on relative paths when cwd()"""
    p = UPath("memory:///foo/bar/baz.txt")
    root = UPath("memory:///foo")
    rel = p.relative_to(root)

    # Memory filesystem doesn't implement cwd(), so these should fail
    with pytest.raises(
        NotImplementedError,
        match=re.escape(
            "fsspec paths can not be relative and MemoryPath.cwd() is unsupported"
        ),
    ):
        _ = rel.path

    with pytest.raises(
        NotImplementedError,
        match=re.escape(
            "fsspec paths can not be relative and MemoryPath.cwd() is unsupported"
        ),
    ):
        rel.exists()


def test_filesystem_operations_work_with_cwd():
    """Test that filesystem operations work on relative paths when cwd()"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test file structure
        test_dir = os.path.join(tmpdir, "testdir")
        os.makedirs(test_dir, exist_ok=True)
        test_file = os.path.join(test_dir, "testfile.txt")
        with open(test_file, "w") as f:
            f.write("test content")

        # Create paths
        abs_path = UPath(test_file)
        abs_dir = UPath(test_dir)
        rel_path = abs_path.relative_to(abs_dir)

        assert not rel_path.is_absolute()
        assert str(rel_path) == "testfile.txt"

        # Change to the test directory and try filesystem operations
        old_cwd = os.getcwd()
        try:
            os.chdir(test_dir)

            # These should work now since we're in the right directory
            full_path = rel_path.path
            assert "testfile.txt" in full_path

            # Test that the file exists
            assert rel_path.exists()

        finally:
            os.chdir(old_cwd)


def test_pickling_relative_paths():
    """Test that relative paths can be pickled and unpickled."""
    p = UPath("memory:///foo/bar/baz.txt")
    root = UPath("memory:///foo")
    rel = p.relative_to(root)

    # Pickle and unpickle
    pickled = pickle.dumps(rel)
    unpickled = pickle.loads(pickled)

    assert str(rel) == str(unpickled)
    assert rel.is_absolute() == unpickled.is_absolute()
    assert rel._relative_base == unpickled._relative_base


def test_with_segments_preserves_relative_state():
    """Test that with_segments preserves the relative state."""
    p = UPath("memory:///foo/bar/baz.txt")
    root = UPath("memory:///foo")
    rel = p.relative_to(root)

    # Create new path with different segments
    new_rel = rel.with_segments("memory:///foo/other/file.txt")

    # Should still be relative with same root
    assert not new_rel.is_absolute()
    assert new_rel._relative_base == rel._relative_base


def test_relative_path_parts():
    """Test that parts work correctly for relative paths."""
    p = UPath("memory:///foo/bar/baz/qux.txt")
    root = UPath("memory:///foo")
    rel = p.relative_to(root)

    assert p.parts == root.parts + rel.parts


def test_absolute_method_behavior():
    """Test that absolute() returns the original absolute path."""
    p = UPath("memory:///foo/bar/baz.txt")
    root = UPath("memory:///foo")
    rel = p.relative_to(root)

    with pytest.raises(
        NotImplementedError,
        match=re.escape("MemoryPath.cwd() is unsupported"),
    ):
        rel.absolute()


def test_is_absolute_method():
    """Test is_absolute() method on relative paths."""
    p = UPath("memory:///foo/bar/baz.txt")
    root = UPath("memory:///foo")
    rel = p.relative_to(root)

    assert not rel.is_absolute()


def test_relative_path_comparison():
    """Test that relative paths can be compared."""
    p1 = UPath("memory:///foo/bar/baz.txt")
    p2 = UPath("memory:///foo/bar/qux.txt")
    root = UPath("memory:///foo")

    rel1 = p1.relative_to(root)
    rel2 = p2.relative_to(root)

    # Compare string representations since .path requires cwd() for memory://
    assert str(rel1) != str(rel2)
    assert rel1 != rel2

    # Same relative path should be equal
    rel1_copy = p1.relative_to(root)
    assert str(rel1) == str(rel1_copy)
    assert rel1 == rel1_copy

    # Same relative path from different base should be equal
    rel3 = UPath("memory:///a/b/c.txt").relative_to(UPath("memory:///a"))
    rel4 = UPath("file:///x/b/c.txt").relative_to(UPath("file:///x"))

    assert str(rel3) == str(rel4)
    assert rel3 == rel4


def test_nonrelative_path_is_absolute():
    """Test that normal (non-relative) paths return True for is_absolute()."""
    p = UPath("memory:///foo/bar/baz.txt")
    assert p.is_absolute()


def test_s3_relative_paths():
    """Test relative paths work with S3 URLs."""
    p = UPath("s3://test_bucket/dir/file.txt")
    root = UPath("s3://test_bucket")
    rel = p.relative_to(root)

    assert not rel.is_absolute()
    assert str(rel) == "dir/file.txt"


@pytest.fixture
def rel_path():
    p = UPath("memory:///foo/bar/baz.txt")
    root = UPath("memory:///foo")
    yield p.relative_to(root)


def test_relative_path_as_uri(rel_path):
    with pytest.raises(
        ValueError,
        match=f"relative path can't be expressed as a {rel_path.protocol} URI",
    ):
        rel_path.as_uri()


@pytest.mark.parametrize(
    "method_args",
    [
        pytest.param(("absolute", ()), id="absolute"),
        pytest.param(("chmod", (0o777,)), id="chmod"),
        pytest.param(("cwd", ()), id="cwd"),
        pytest.param(("exists", ()), id="exists"),
        pytest.param(("glob", ("*.txt",)), id="glob"),
        pytest.param(("group", ()), id="group"),
        pytest.param(("is_dir", ()), id="is_dir"),
        pytest.param(("is_file", ()), id="is_file"),
        pytest.param(("is_symlink", ()), id="is_symlink"),
        pytest.param(("iterdir", ()), id="iterdir"),
        pytest.param(("lchmod", (0o777,)), id="lchmod"),
        pytest.param(("lstat", ()), id="lstat"),
        pytest.param(("mkdir", ()), id="mkdir"),
        pytest.param(("open", ()), id="open"),
        pytest.param(("owner", ()), id="owner"),
        pytest.param(("read_bytes", ()), id="read_bytes"),
        pytest.param(("read_text", ()), id="read_text"),
        pytest.param(("readlink", ()), id="readlink"),
        pytest.param(("rename", ("a/b/c",)), id="rename"),
        pytest.param(("replace", ("...",)), id="replace"),
        pytest.param(("resolve", ()), id="resolve"),
        pytest.param(("rglob", ("*.txt",)), id="rglob"),
        pytest.param(("rmdir", ()), id="rmdir"),
        pytest.param(("samefile", ("...",)), id="samefile"),
        pytest.param(("stat", ()), id="stat"),
        pytest.param(("symlink_to", ("...",)), id="symlink_to"),
        pytest.param(("touch", ()), id="touch"),
        pytest.param(("unlink", ()), id="unlink"),
        pytest.param(("write_bytes", (b"data",)), id="write_bytes"),
        pytest.param(("write_text", ("data",)), id="write_text"),
    ],
)
def test_path_operations_disabled_without_cwd(rel_path, method_args):
    """UPaths without .cwd() implementation should not allow path operations."""
    method, args = method_args

    with pytest.raises(NotImplementedError):
        # next only needs to be called for iterdir and glob/rglob
        # but the other raise already in the getattr call
        next(getattr(rel_path, method)(*args))


@pytest.mark.parametrize(
    "protocol,path,base",
    [
        ("", "/foo/bar/baz.txt", "/foo"),
        ("file", "/foo/bar/baz.txt", "/foo"),
        ("s3", "s3://bucket/foo/bar/baz.txt", "s3://bucket/foo"),
        ("gcs", "gcs://bucket/foo/bar/baz.txt", "gcs://bucket/foo"),
        ("ftp", "ftp://user:pass@host/foo/bar/baz.txt", "ftp://user:pass@host/foo"),
        ("http", "http://host/foo/bar/baz.txt", "http://host/foo"),
        ("https", "https://host/foo/bar/baz.txt", "https://host/foo"),
        ("memory", "memory:///foo/bar/baz.txt", "memory:///foo"),
    ],
)
def test_drive_root_anchor_empty_for_relative_paths(protocol, path, base):
    rel = UPath(path, protocol=protocol).relative_to(UPath(base, protocol=protocol))
    assert (rel.drive, rel.root, rel.anchor) == ("", "", "")


@pytest.mark.parametrize(
    "protocol,path,base,expected_rel",
    [
        ("", "/foo/bar/baz.txt", "/foo", "bar/baz.txt"),
        ("file", "/foo/bar/baz.txt", "/foo", "bar/baz.txt"),
        ("s3", "s3://bucket/foo/bar/baz.txt", "s3://bucket/foo", "bar/baz.txt"),
        ("gcs", "gcs://bucket/foo/bar/baz.txt", "gcs://bucket/foo", "bar/baz.txt"),
        (
            "ftp",
            "ftp://user:pass@host/foo/bar/baz.txt",
            "ftp://user:pass@host/foo",
            "bar/baz.txt",
        ),
        ("http", "http://host/foo/bar/baz.txt", "http://host/foo", "bar/baz.txt"),
        ("https", "https://host/foo/bar/baz.txt", "https://host/foo", "bar/baz.txt"),
        ("memory", "memory:///foo/bar/baz.txt", "memory:///foo", "bar/baz.txt"),
    ],
)
def test_relative_path_properties(protocol, path, base, expected_rel):
    rel = UPath(path, protocol=protocol).relative_to(UPath(base, protocol=protocol))

    assert not rel.is_absolute()
    assert rel.as_posix() == expected_rel
    assert rel.parts == tuple(expected_rel.split("/"))


@pytest.mark.parametrize(
    "protocol,path,base,expected_parts",
    [
        ("", "/foo/bar/baz.txt", "/foo", ("bar", "baz.txt")),
        ("file", "/foo/bar/baz.txt", "/foo", ("bar", "baz.txt")),
        ("s3", "s3://bucket/foo/bar/baz.txt", "s3://bucket/foo", ("bar", "baz.txt")),
        ("gcs", "gcs://bucket/foo/bar/baz.txt", "gcs://bucket/foo", ("bar", "baz.txt")),
        (
            "ftp",
            "ftp://user:pass@host/foo/bar/baz.txt",
            "ftp://user:pass@host/foo",
            ("bar", "baz.txt"),
        ),
        ("http", "http://host/foo/bar/baz.txt", "http://host/foo", ("bar", "baz.txt")),
        (
            "https",
            "https://host/foo/bar/baz.txt",
            "https://host/foo",
            ("bar", "baz.txt"),
        ),
        ("memory", "memory:///foo/bar/baz.txt", "memory:///foo", ("bar", "baz.txt")),
    ],
)
def test_relative_path_parts_property(protocol, path, base, expected_parts):
    rel = UPath(path, protocol=protocol).relative_to(UPath(base, protocol=protocol))
    assert rel.parts == expected_parts


def test_relative_path_is_something(rel_path):
    assert rel_path.is_block_device() is False
    assert rel_path.is_char_device() is False
    assert rel_path.is_fifo() is False
    assert rel_path.is_mount() is False
    assert rel_path.is_reserved() is False
    assert rel_path.is_socket() is False


def test_relative_path_hashable():
    x = UPath("memory:///a/b/c.txt")
    y = x.relative_to(UPath("memory:///a"))
    assert hash(y) != hash(x)


def test_relative_path_expanduser_noop(rel_path):
    # this should be revisited if we ever add ~ support to non-file protocols
    assert rel_path == rel_path.expanduser()


def test_relative_path_stem_suffix_name(rel_path):
    assert rel_path.name == "baz.txt"
    assert rel_path.stem == "baz"
    assert rel_path.suffix == ".txt"
    assert rel_path.suffixes == [".txt"]
    assert rel_path.with_name("other.txt").name == "other.txt"
    assert rel_path.with_stem("other").name == "other.txt"
    assert rel_path.with_suffix(".md").name == "baz.md"
    assert rel_path.with_suffix(".tar.gz").suffixes == [".tar", ".gz"]


@pytest.mark.parametrize(
    "protocol,pth,base,expected_parent",
    [
        ("", "/foo/bar/baz.txt", "/foo", "bar"),
        ("", "/foo", "/foo", "."),
        ("file", "/foo/bar/baz.txt", "/foo", "bar"),
        ("file", "/foo/bar", "/foo/bar", "."),
        ("s3", "s3://bucket/foo/bar/baz.txt", "s3://bucket/foo", "bar"),
        ("s3", "s3://bucket/foo/bar/", "s3://bucket/foo/bar", "."),
        ("gcs", "gcs://bucket/foo/bar/baz.txt", "gcs://bucket/foo", "bar"),
        ("gcs", "gcs://bucket/foo/bar/", "gcs://bucket/foo", "."),
        ("memory", "memory:///foo/bar/baz.txt", "memory:///foo", "bar"),
        ("memory", "memory:///foo/bar", "memory:///foo", "."),
        ("https", "https://host/foo/bar/baz.txt", "https://host/foo", "bar"),
        ("https", "https://host/foo/bar/", "https://host/foo/bar", "."),
    ],
)
def test_relative_path_parent(protocol, pth, base, expected_parent):
    rel = UPath(pth, protocol=protocol).relative_to(UPath(base, protocol=protocol))
    assert str(rel.parent) == expected_parent


@pytest.mark.parametrize(
    "uri,base,expected_parents_parts",
    [
        ("/foo/bar/baz/qux.txt", "/foo", [("bar", "baz"), ("bar",), ()]),
        ("file:///foo/bar/baz/qux.txt", "file:///foo", [("bar", "baz"), ("bar",), ()]),
        ("s3://bucket/foo/bar/baz/", "s3://bucket/", [("foo", "bar"), ("foo",), ()]),
        ("gcs://bucket/foo/bar/baz", "gcs://bucket/", [("foo", "bar"), ("foo",), ()]),
        ("az://bucket/foo/bar/baz", "az://bucket/", [("foo", "bar"), ("foo",), ()]),
        (
            "memory:///foo/bar/baz/qux.txt",
            "memory:///foo",
            [("bar", "baz"), ("bar",), ()],
        ),
        (
            "https://host.com/foo/bar/baz/qux.txt",
            "https://host.com/foo",
            [("bar", "baz"), ("bar",), ()],
        ),
    ],
)
def test_relative_path_parents(uri, base, expected_parents_parts):
    rel = UPath(uri).relative_to(UPath(base))
    parents = list(rel.parents)
    assert [x.parts for x in parents] == expected_parents_parts


@pytest.mark.parametrize(
    "protocol,pth,base",
    [
        ("", "/foo/bar/baz.txt", "/foo"),
        ("file", "/foo/bar/baz.txt", "/foo"),
    ],
)
def test_home_works_for_local_paths(protocol, pth, base):
    rel = UPath(pth, protocol=protocol).relative_to(UPath(base, protocol=protocol))
    prefix = f"{protocol}://" if protocol else ""
    assert rel.home().as_posix() == prefix + UPath.home().as_posix()


@pytest.mark.parametrize(
    "protocol,pth,base",
    [
        ("s3", "s3://bucket/foo/bar/baz.txt", "s3://bucket/foo"),
        ("gcs", "gcs://bucket/foo/bar/baz.txt", "gcs://bucket/foo"),
        ("memory", "memory:///foo/bar/baz.txt", "memory:///foo"),
        ("https", "https://host/foo/bar/baz.txt", "https://host/foo"),
    ],
)
def test_home_raises_for_non_local_paths(protocol, pth, base):
    rel = UPath(pth, protocol=protocol).relative_to(UPath(base, protocol=protocol))
    with pytest.raises(
        NotImplementedError,
        match=re.escape(f"{type(rel).__name__}.home() is unsupported"),
    ):
        rel.home()


@pytest.mark.parametrize(
    "protocol,pth,base",
    [
        ("", "/foo/bar/baz.txt", "/foo"),
        ("file", "/foo/bar/baz.txt", "/foo"),
        ("s3", "s3://bucket/foo/bar/baz.txt", "s3://bucket/foo"),
        ("gcs", "gcs://bucket/foo/bar/baz.txt", "gcs://bucket/foo"),
        ("memory", "memory:///foo/bar/baz.txt", "memory:///foo"),
        ("https", "https://host/foo/bar/baz.txt", "https://host/foo"),
    ],
)
def test_parser_attribute_available(protocol, pth, base):
    rel_path = UPath(pth, protocol=protocol).relative_to(UPath(base, protocol=protocol))
    assert rel_path.parser is not None


@pytest.mark.parametrize(
    "protocol",
    [
        "",
        "file",
    ],
)
def test_relpath_path_resolve(tmp_path, protocol, monkeypatch):
    """This should work for all path types that support .cwd()"""
    base = UPath(tmp_path, protocol=protocol)
    (base / "a" / "b").mkdir(parents=True)
    (base / "a" / "b" / "file.txt").write_text("data")
    monkeypatch.chdir(base)

    rel = UPath("/xyz/a/b/c/d/../../file.txt", protocol=protocol).relative_to(
        UPath("/xyz", protocol=protocol)
    )

    assert rel.as_posix() == "a/b/c/d/../../file.txt"

    resolved = rel.resolve()
    prefix = f"{protocol}://" if protocol else ""
    assert (
        resolved.as_posix() == prefix + (tmp_path / "a" / "b" / "file.txt").as_posix()
    )
    assert resolved.read_text() == "data"
    assert resolved.is_absolute()
    assert resolved.exists()


@pytest.mark.parametrize(
    "protocol,path,base",
    [
        ("", "/foo/bar/baz/qux.txt", "/foo"),
        ("file", "/foo/bar/baz/qux.txt", "/foo"),
        ("s3", "s3://bucket/foo/bar/baz/qux.txt", "s3://bucket/foo"),
        ("gcs", "gcs://bucket/foo/bar/baz/qux.txt", "gcs://bucket/foo"),
        ("memory", "memory:///foo/bar/baz/qux.txt", "memory:///foo"),
        ("https", "https://host/foo/bar/baz/qux.txt", "https://host/foo"),
    ],
)
def test_relative_path_match(protocol, path, base):
    """Test that match works correctly for relative paths."""
    rel = UPath(path, protocol=protocol).relative_to(UPath(base, protocol=protocol))

    assert rel.as_posix() == "bar/baz/qux.txt"

    # Should match patterns that match the relative path
    assert rel.match("bar/baz/qux.txt")
    assert rel.match("*/baz/qux.txt")
    assert rel.match("bar/*/qux.txt")
    assert rel.match("*/**/*.txt")  # ** acts like *

    # Should not match patterns that don't match
    assert not rel.match("foo/baz/qux.txt")
    assert not rel.match("*.py")
    assert not rel.match("other.txt")


@pytest.mark.parametrize(
    "protocol,path,base",
    [
        ("", "/foo/bar/baz/qux.txt", "/foo"),
        ("file", "/foo/bar/baz/qux.txt", "/foo"),
        ("s3", "s3://bucket/foo/bar/baz/qux.txt", "s3://bucket/foo"),
        ("gcs", "gcs://bucket/foo/bar/baz/qux.txt", "gcs://bucket/foo"),
        ("memory", "memory:///foo/bar/baz/qux.txt", "memory:///foo"),
        ("https", "https://host/foo/bar/baz/qux.txt", "https://host/foo"),
    ],
)
def test_relative_path_joinpath(protocol, path, base):
    """Test that joinpath works correctly for relative paths."""
    rel = UPath(path, protocol=protocol).relative_to(UPath(base, protocol=protocol))

    # Test joining with a single segment
    assert rel.as_posix() == "bar/baz/qux.txt"
    joined = rel.joinpath("extra.txt")
    assert joined.as_posix() == "bar/baz/qux.txt/extra.txt"
    assert not joined.is_absolute()

    # Test joining with multiple segments
    joined_multi = rel.joinpath("dir", "file.py")
    assert joined_multi.as_posix() == "bar/baz/qux.txt/dir/file.py"
    assert not joined_multi.is_absolute()

    # Test that the result is still relative with same base
    assert joined.protocol == joined_multi.protocol == protocol
    assert joined.storage_options == joined_multi.storage_options == rel.storage_options


@pytest.mark.parametrize(
    "protocol,path,base",
    [
        ("", "/foo/bar/baz/qux.txt", "/foo"),
        ("file", "/foo/bar/baz/qux.txt", "/foo"),
        ("s3", "s3://bucket/foo/bar/baz/qux.txt", "s3://bucket/foo"),
        ("gcs", "gcs://bucket/foo/bar/baz/qux.txt", "gcs://bucket/foo"),
        ("memory", "memory:///foo/bar/baz/qux.txt", "memory:///foo"),
        ("https", "https://host/foo/bar/baz/qux.txt", "https://host/foo"),
    ],
)
def test_join_local_absolute_path_to_relative(protocol, path, base, tmp_path):
    """Test that joining an absolute path to a relative path works correctly."""
    rel = UPath(path, protocol=protocol).relative_to(base)

    assert rel.as_posix() == "bar/baz/qux.txt"
    tmp_path.joinpath("bar/baz/qux.txt").parent.mkdir(parents=True, exist_ok=True)
    tmp_path.joinpath("bar/baz/qux.txt").write_text("data")

    assert UPath(tmp_path).joinpath(rel).read_text() == "data"


@pytest.mark.parametrize(
    "protocol,path",
    [
        ("", "/foo/bar"),
        ("file", "/foo/bar"),
        ("s3", "s3://bucket/foo/bar"),
        ("gcs", "gcs://bucket/foo/bar"),
        ("memory", "memory:///foo/bar"),
        ("https", "https://host/foo/bar"),
    ],
)
def test_join_fsspec_absolute_path_to_relative(protocol, path):
    p = UPath(path, protocol=protocol)

    x = p.joinpath(Path("a/b/c").as_posix())
    assert x.path.endswith("foo/bar/a/b/c")


@pytest.mark.parametrize(
    "proto0,path0",
    [
        ("", "/foo/bar"),
        ("file", "/foo/bar"),
        ("s3", "s3://bucket/foo/bar"),
        ("gcs", "gcs://bucket/foo/bar"),
        ("memory", "memory:///foo/bar"),
        ("https", "https://host/foo/bar"),
    ],
)
@pytest.mark.parametrize(
    "proto1,path1,base1",
    [
        ("", "/foo/bar", "/foo"),
        ("file", "/foo/bar", "/foo"),
        ("s3", "s3://bucket/foo/bar", "s3://bucket/foo"),
        ("gcs", "gcs://bucket/foo/bar", "gcs://bucket/foo"),
        ("memory", "memory:///foo/bar", "memory:///foo"),
        ("https", "https://host/foo/bar", "https://host/foo"),
    ],
)
def test_join_fsspec_absolute_path_to_fsspec_relative(
    proto0, path0, proto1, path1, base1
):
    p0 = UPath(path0, protocol=proto0)
    p1 = UPath(path1, protocol=proto1).relative_to(base1)
    assert str(p1) == "bar"

    x = p0.joinpath(p1)
    assert x.path.endswith("foo/bar/bar")
