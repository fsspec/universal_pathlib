"""Semantics of the special paths "", ".", "..", "/" across UPath flavours.

The behavior tested here is documented in `docs/concepts/special-paths.md`.
All tests are pure: they construct paths, but never access a filesystem.

Known deviations from the documented semantics are marked as strict xfails.
Each one references a candidate bug (see `KNOWN_ISSUES` below).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from upath import UnsupportedOperation
from upath import UPath

SPECIAL_INPUTS = ["", ".", "..", "/", "./a", "a/..", "a/./b", "a//b", "a/", "a/b/"]
RELATIVE_INPUTS = [x for x in SPECIAL_INPUTS if x.strip("/")]

# (b) fsspec filesystems with a single root (root_marker "/" or "")
ROOTED = {
    "memory": "memory:///{}",
    "file": "file:///{}",
    "sftp": "sftp://host/{}",
    "smb": "smb://host/{}",
    "ftp": "ftp://host/{}",
    "hdfs": "hdfs:///{}",
    "webdav": "webdav+https://host.com/{}",
    "github": "github://fsspec:universal_pathlib@main/{}",
    "hf": "hf://{}",
    "zip": "zip://{}::memory:///archive.zip",
    "tar": "tar://{}::memory:///archive.tar",
}
# (c) fsspec filesystems anchored at a bucket, container or netloc
ANCHORED = {
    "s3": "s3://bucket/{}",
    "gcs": "gs://bucket/{}",
    "az": "az://container/{}",
    "abfs": "abfs://container/{}",
    "https": "https://example.com/{}",
}
FSSPEC = {**ROOTED, **ANCHORED}

MEANINGFUL_TRAILING_SLASH = {"https"}
# LocalFileSystem makes relative paths absolute using the current working dir
CWD_RELATIVE = {"file"}

KNOWN_ISSUES = {
    "relative-not-rooted": (
        "candidate bug: relative paths given with protocol= are not rooted"
        " on sftp, smb and hdfs (not absolute, str() does not roundtrip)"
    ),
    "resolve-no-anchor-part": (
        "candidate bug: resolve() skips the first part when .parts has no"
        " anchor element (github, webdav) and leaves '..' in the result"
    ),
    "parts-root-without-anchor": (
        "candidate bug: .parts[0] is '/' although .anchor is '' (zip, tar, hf)"
    ),
    "webdav-uri-leading-slash": (
        "candidate bug: webdav uris keep a leading '/' in .path and .name"
        " and differ from the equivalent joined path"
    ),
    "github-uri-trailing-slash": (
        "candidate bug: github uris keep a trailing '/' in .path"
        " and differ from the equivalent joined path"
    ),
    "github-dot": "candidate bug: GitHubPath.path collapses '.' while str() keeps it",
    "cloud-empty-parts": (
        "candidate bug: .parts drops empty segments on bucket-anchored"
        " filesystems that support empty parts (s3, gcs, az, abfs)"
    ),
    "absolute-segment-join": (
        "candidate bug: joining a segment with a leading '/' keeps the '/'"
        " on root_marker='' filesystems (github, webdav, hf, tar)"
    ),
    "hdfs-trailing-slash": "candidate bug: hdfs keeps trailing slashes",
    "http-final-dotdot": (
        "candidate bug: a final '..' drops the trailing slash on http(s) paths"
    ),
}


def _xfail(issue: str) -> pytest.MarkDecorator:
    return pytest.mark.xfail(strict=True, reason=KNOWN_ISSUES[issue])


def _params(protocols, xfail: dict[str, str] | None = None) -> list:
    """parametrize protocols, marking known issues as strict xfails"""
    xfail = xfail or {}
    params = []
    for protocol in sorted(protocols):
        marks = []
        if protocol in xfail:
            marks.append(_xfail(xfail[protocol]))
        if protocol == "file":
            marks.append(
                pytest.mark.skipif(sys.platform == "win32", reason="posix root")
            )
        params.append(pytest.param(protocol, marks=marks))
    return params


def _root(protocol: str) -> UPath:
    return UPath(FSSPEC[protocol].format(""))


def _uri(protocol: str, path: str) -> UPath:
    return UPath(FSSPEC[protocol].format(path))


def _kw(protocol: str, path: str) -> UPath:
    root = _root(protocol)
    return UPath(path, protocol=root.protocol, **root.storage_options)


def _resolve(pth: UPath) -> UPath:
    if pth.protocol in {"http", "https"}:
        return pth.resolve(follow_redirects=False)  # type: ignore[call-arg]
    return pth.resolve()


NOT_ROOTED = dict.fromkeys(["sftp", "smb", "hdfs"], "relative-not-rooted")
NO_ANCHOR_PART = dict.fromkeys(["github", "webdav"], "resolve-no-anchor-part")


# === (a) pathlib-backed local paths ==================================


@pytest.mark.parametrize("pth", SPECIAL_INPUTS)
def test_local_special_paths_match_pathlib(pth):
    p = UPath(pth)
    q = Path(pth)
    assert isinstance(p, Path)
    assert p == UPath(q)
    assert str(p) == str(q)
    assert p.parts == q.parts
    assert p.anchor == q.anchor
    assert p.is_absolute() is q.is_absolute()
    assert p.name == q.name
    assert str(p.parent) == str(q.parent)


def test_local_empty_path_is_dot():
    assert UPath("") == UPath(".")
    assert UPath("").parts == ()
    assert not UPath("").is_absolute()


def test_local_dotdot_is_kept():
    p = UPath("a") / ".."
    assert p.name == ".."
    assert p.parent == UPath("a")
    assert p != UPath(".")


# === (b) + (c) fsspec-backed paths ===================================


@pytest.mark.parametrize("protocol", _params(set(ROOTED) - CWD_RELATIVE))
def test_empty_path_is_root(protocol):
    root = _root(protocol)
    assert _kw(protocol, "") == root
    assert _kw(protocol, "/") == root
    assert _uri(protocol, "/") == root


@pytest.mark.parametrize("protocol", ["s3", "gcs", "az", "abfs"])
def test_empty_path_has_no_bucket(protocol):
    root = _root(protocol)
    assert _kw(protocol, "") == _kw(protocol, "/")
    assert _kw(protocol, "").drive == ""
    assert _kw(protocol, "").joinpath(root.drive) == root


@pytest.mark.parametrize(
    "pth,expected", [("", ""), (".", ""), ("a", "a"), ("a/b", "a/b")]
)
def test_file_relative_input_is_cwd_relative(pth, expected, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cwd = UPath(os.getcwd(), protocol="file")
    assert UPath(pth, protocol="file") == cwd.joinpath(expected)


@pytest.mark.parametrize(
    "protocol,pth",
    [
        pytest.param(
            protocol,
            pth,
            marks=(
                [_xfail(NOT_ROOTED[protocol])]
                if protocol in NOT_ROOTED and pth in RELATIVE_INPUTS
                else []
            ),
        )
        for protocol in sorted(set(FSSPEC) - {"https"})
        for pth in SPECIAL_INPUTS
    ],
)
def test_fsspec_paths_are_absolute(protocol, pth):
    assert _kw(protocol, pth).is_absolute()
    assert _uri(protocol, pth).is_absolute()
    assert _root(protocol).joinpath(pth).is_absolute()


@pytest.mark.parametrize("pth", ["a", "a/b"])
@pytest.mark.parametrize("protocol", _params(set(ROOTED) - CWD_RELATIVE, NOT_ROOTED))
def test_relative_input_is_relative_to_root(protocol, pth):
    assert _kw(protocol, pth) == _root(protocol).joinpath(pth)


@pytest.mark.parametrize(
    "protocol,make",
    [
        pytest.param(
            protocol,
            make,
            marks=(
                [_xfail("relative-not-rooted")]
                if make == "kw" and protocol in NOT_ROOTED
                else []
            ),
        )
        for protocol in sorted(set(ROOTED) - CWD_RELATIVE)
        for make in ["kw", "uri", "join"]
    ],
)
def test_str_roundtrip(protocol, make):
    for pth in SPECIAL_INPUTS:
        if make == "kw":
            p = _kw(protocol, pth)
        elif make == "uri":
            if protocol == "github" and pth.endswith("/") and pth != "/":
                continue  # see test_uri_equals_joined_path
            p = _uri(protocol, pth)
        else:
            p = _root(protocol).joinpath(pth)
        assert UPath(str(p), **p.storage_options) == p


@pytest.mark.parametrize("protocol", _params(FSSPEC, {"hdfs": "hdfs-trailing-slash"}))
def test_join_empty_segment(protocol):
    root = _root(protocol)
    assert root / "" == root
    if protocol in MEANINGFUL_TRAILING_SLASH:
        # an empty final segment is a trailing slash
        assert root / "a" / "" == root / "a/"
    else:
        assert root / "a" / "" == root / "a"


@pytest.mark.parametrize("protocol", _params(FSSPEC, {"hdfs": "hdfs-trailing-slash"}))
def test_trailing_slash(protocol):
    root = _root(protocol)
    if protocol in MEANINGFUL_TRAILING_SLASH:
        assert root / "a/" != root / "a"
        assert str(root / "a/").endswith("/")
    else:
        assert root / "a/" == root / "a"
        assert root / "a/b/" == root / "a/b"


@pytest.mark.parametrize(
    "protocol,pth",
    [
        pytest.param(
            protocol,
            pth,
            marks=(
                [_xfail("webdav-uri-leading-slash")]
                if protocol == "webdav"
                else (
                    [_xfail("github-uri-trailing-slash")]
                    if protocol == "github" and pth.endswith("/")
                    else []
                )
            ),
        )
        for protocol in sorted(FSSPEC)
        for pth in ["a", "a/b", "a/"]
    ],
)
def test_uri_equals_joined_path(protocol, pth):
    p = _uri(protocol, pth)
    assert p == _root(protocol).joinpath(pth)
    if pth.endswith("/") and protocol in MEANINGFUL_TRAILING_SLASH:
        assert p.name == ""
    else:
        assert p.name == pth.rstrip("/").rpartition("/")[2]


@pytest.mark.parametrize("protocol", _params(FSSPEC))
def test_dot_segments_are_preserved(protocol):
    root = _root(protocol)
    p = root / "a/./b"
    assert p != root / "a/b"
    assert p.path.endswith("a/./b")
    p = root / "a/.."
    assert p != root
    assert p.name == ".."
    assert p.parent == root / "a"
    assert _uri(protocol, "a/../b").path.endswith("a/../b")


@pytest.mark.parametrize(
    "protocol",
    _params(set(ROOTED) - CWD_RELATIVE, {**NOT_ROOTED, "github": "github-dot"}),
)
def test_single_dot_is_not_collapsed(protocol):
    p = _kw(protocol, ".")
    assert p != _root(protocol)
    assert p.name == "."


@pytest.mark.parametrize("protocol", _params(FSSPEC, NO_ANCHOR_PART))
def test_resolve_normalizes_dot_segments(protocol):
    root = _root(protocol)
    for pth, expected in [
        ("a/./b", "a/b"),
        ("a/b/../c", "a/c"),
        ("./a", "a"),
        ("../a", "a"),
    ]:
        r = _resolve(root / pth)
        assert "." not in r.parts
        assert ".." not in r.parts
        assert r == root / expected


@pytest.mark.parametrize("protocol", _params(FSSPEC, NO_ANCHOR_PART))
def test_resolve_does_not_go_above_the_anchor(protocol):
    root = _root(protocol)
    assert _resolve(root / ".") == root
    assert _resolve(root / "..") == root
    assert _resolve(root / "a/..") == root
    assert _resolve(root / "a/../..") == root


@pytest.mark.parametrize(
    "protocol",
    _params(set(ROOTED) - CWD_RELATIVE, {**NOT_ROOTED, **NO_ANCHOR_PART}),
)
def test_resolve_dot_is_root(protocol):
    assert _resolve(_kw(protocol, ".")) == _root(protocol)
    assert _resolve(_kw(protocol, "..")) == _root(protocol)


@pytest.mark.parametrize("protocol", _params(FSSPEC))
def test_root_is_its_own_parent(protocol):
    root = _root(protocol)
    assert root.parent == root
    assert root.is_absolute()


@pytest.mark.parametrize("protocol", _params(FSSPEC))
def test_parent_of_child(protocol):
    root = _root(protocol)
    assert (root / "a").parent == root
    assert (root / "a/b").parent == root / "a"
    assert (root / "a").name == "a"


@pytest.mark.parametrize(
    "protocol",
    _params(FSSPEC, dict.fromkeys(["zip", "tar", "hf"], "parts-root-without-anchor")),
)
def test_parts_start_with_anchor(protocol):
    p = _root(protocol) / "a/b"
    if p.anchor:
        assert p.parts == (p.anchor, "a", "b")
    else:
        assert p.parts == ("a", "b")


@pytest.mark.parametrize("pth", ["a", "a/b", "a/./b", "a/.."])
@pytest.mark.parametrize("protocol", _params(FSSPEC))
def test_parts_roundtrip(protocol, pth):
    p = _root(protocol) / pth
    assert p.with_segments(*p.parts) == p


@pytest.mark.parametrize(
    "protocol",
    _params(
        ROOTED,
        dict.fromkeys(["github", "webdav", "hf", "tar"], "absolute-segment-join"),
    ),
)
def test_join_absolute_segment_restarts_at_root(protocol):
    root = _root(protocol)
    assert root / "a" / "/b" == root / "b"


# === (c) bucket / netloc anchored paths ==============================


@pytest.mark.parametrize("protocol", sorted(ANCHORED))
def test_anchor_is_bucket_or_netloc(protocol):
    root = _root(protocol)
    assert root.anchor
    assert root.parts[0] == root.anchor
    assert (root / "a").anchor == root.anchor


@pytest.mark.parametrize(
    "protocol",
    _params(ANCHORED, dict.fromkeys(["s3", "gcs", "az", "abfs"], "cloud-empty-parts")),
)
def test_empty_parts_are_supported(protocol):
    root = _root(protocol)
    p = root / "a//b"
    assert p != root / "a/b"
    assert p.parts == (root.anchor, "a", "", "b")


@_xfail("http-final-dotdot")
def test_http_resolve_final_dotdot_is_a_directory():
    # RFC 3986, section 5.2.4: "/a/b/.." normalizes to "/a/"
    p = UPath("https://example.com/a/b/..")
    assert _resolve(p) == UPath("https://example.com/a/")


# === (d) non-joinable paths ==========================================


@pytest.mark.parametrize("segment", ["", ".", "..", "/", "a"])
def test_data_path_is_not_joinable(segment):
    p = UPath("data:text/plain;base64,aGVsbG8=")
    with pytest.raises(UnsupportedOperation):
        p.joinpath(segment)
    with pytest.raises(UnsupportedOperation):
        p / segment


def test_data_path_is_its_own_anchor():
    p = UPath("data:text/plain;base64,aGVsbG8=")
    assert p.is_absolute()
    assert p.anchor == ""
    assert p.parts == (p.path,)
    assert p.parent == p
    assert p.resolve() == p
