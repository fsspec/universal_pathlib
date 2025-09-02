from pathlib import Path

import pytest

from upath import UPath

DRIVE_ROOT_ANCHOR_TESTS = [
    # cloud
    ("s3://bucket", "bucket", "/", "bucket/", ("bucket/",)),
    ("s3://bucket/a", "bucket", "/", "bucket/", ("bucket/", "a")),
    ("gs://bucket", "bucket", "/", "bucket/", ("bucket/",)),
    ("gs://bucket/a", "bucket", "/", "bucket/", ("bucket/", "a")),
    ("az://bucket", "bucket", "/", "bucket/", ("bucket/",)),
    ("az://bucket/a", "bucket", "/", "bucket/", ("bucket/", "a")),
    # data
    (
        "data:text/plain,A%20brief%20note",
        "",
        "",
        "",
        ("data:text/plain,A%20brief%20note",),
    ),
    # github
    ("github://user:token@repo/abc", "", "", "", ("abc",)),
    # hdfs
    ("hdfs://a/b/c", "", "/", "/", ("/", "b", "c")),
    ("hdfs:///a/b/c", "", "/", "/", ("/", "a", "b", "c")),
    # http
    ("http://a/", "http://a", "/", "http://a/", ("http://a/", "")),
    ("http://a/b/c", "http://a", "/", "http://a/", ("http://a/", "b", "c")),
    ("https://a/b/c", "https://a", "/", "https://a/", ("https://a/", "b", "c")),
    # memory
    ("memory://a/b/c", "", "/", "/", ("/", "a", "b", "c")),
    ("memory:///a/b/c", "", "/", "/", ("/", "a", "b", "c")),
    # sftp
    ("sftp://a/b/c", "", "/", "/", ("/", "b", "c")),
    ("sftp:///a/b/c", "", "/", "/", ("/", "a", "b", "c")),
    # smb
    ("smb://a/b/c", "", "/", "/", ("/", "b", "c")),
    ("smb:///a/b/c", "", "/", "/", ("/", "a", "b", "c")),
    # webdav
    ("webdav+http://host.com/a/b/c", "", "", "", ("a", "b", "c")),
    ("webdav+http://host.com/a/b/c", "", "", "", ("a", "b", "c")),
    # local
    (
        "file:///a/b/c",
        Path("/a/b/c").absolute().drive,
        Path("/").absolute().root.replace("\\", "/"),
        Path("/").absolute().anchor.replace("\\", "/"),
        tuple(x.replace("\\", "/") for x in Path("/a/b/c").absolute().parts),
    ),
]


@pytest.mark.parametrize(
    "path,drive,root,anchor",
    [x[0:4] for x in DRIVE_ROOT_ANCHOR_TESTS],
)
def test_drive_root_anchor(path, drive, root, anchor):
    p = UPath(path)
    assert (p.drive, p.root, p.anchor) == (drive, root, anchor)


@pytest.mark.parametrize(
    "path,parts",
    [(x[0], x[4]) for x in DRIVE_ROOT_ANCHOR_TESTS],
)
def test_parts(path, parts):
    p = UPath(path)
    assert p.parts == parts
