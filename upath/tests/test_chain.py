import copy
import os
from pathlib import Path

import pytest
from fsspec.core import url_to_fs
from fsspec.implementations.memory import MemoryFileSystem

from upath import UPath
from upath._chain import FSSpecChainParser


@pytest.mark.parametrize(
    "urlpath,expected",
    [
        ("simplecache::file://tmp", "simplecache"),
        ("zip://file.txt::file://tmp.zip", "zip"),
    ],
)
def test_chaining_upath_protocol(urlpath, expected):
    pth = UPath(urlpath)
    assert pth.protocol == expected


def add_current_drive_on_windows(pth: str) -> str:
    drive = os.path.splitdrive(Path.cwd().as_posix())[0]
    return f"{drive}{pth}"


@pytest.mark.parametrize(
    "urlpath,expected",
    [
        pytest.param(
            "simplecache::file:///tmp",
            add_current_drive_on_windows("/tmp"),
        ),
        pytest.param(
            "zip://file.txt::file:///tmp.zip",
            "file.txt",
        ),
        pytest.param(
            "zip://a/b/c.txt::simplecache::memory://zipfile.zip",
            "a/b/c.txt",
        ),
    ],
)
def test_chaining_upath_path(urlpath, expected):
    pth = UPath(urlpath)
    assert pth.path == expected


@pytest.mark.parametrize(
    "urlpath,expected",
    [
        (
            "simplecache::file:///tmp",
            {
                "target_protocol": "file",
                "target_options": {},
            },
        ),
    ],
)
def test_chaining_upath_storage_options(urlpath, expected):
    pth = UPath(urlpath)
    assert dict(pth.storage_options) == expected


@pytest.mark.parametrize(
    "urlpath,expected",
    [
        ("simplecache::memory://tmp", ("/", "tmp")),
    ],
)
def test_chaining_upath_parts(urlpath, expected):
    pth = UPath(urlpath)
    assert pth.parts == expected


@pytest.mark.parametrize(
    "urlpath,expected",
    [
        ("simplecache::memory:///tmp", "simplecache::memory:///tmp"),
    ],
)
def test_chaining_upath_str(urlpath, expected):
    pth = UPath(urlpath)
    assert str(pth) == expected


@pytest.fixture
def clear_memory_fs():
    fs = MemoryFileSystem()
    store = fs.store
    pseudo_dirs = fs.pseudo_dirs
    try:
        yield fs
    finally:
        fs.store.clear()
        fs.store.update(store)
        fs.pseudo_dirs[:] = pseudo_dirs


@pytest.fixture
def memory_file_urlpath(clear_memory_fs):
    fs = clear_memory_fs
    fs.pipe_file("/abc/file.txt", b"hello world")
    yield fs.unstrip_protocol("/abc/file.txt")


def test_read_file(memory_file_urlpath):
    pth = UPath(f"simplecache::{memory_file_urlpath}")
    assert pth.read_bytes() == b"hello world"


def test_write_file(clear_memory_fs):
    pth = UPath("simplecache::memory://abc.txt")
    pth.write_bytes(b"hello world")
    assert clear_memory_fs.cat_file("abc.txt") == b"hello world"


@pytest.mark.parametrize(
    "urlpath",
    [
        "memory:///file.txt",
        "simplecache::memory:///tmp",
        "zip://file.txt::memory:///tmp.zip",
        "zip://a/b/c.txt::simplecache::memory:///zipfile.zip",
        "simplecache::zip://a/b/c.txt::tar://blah.zip::memory:///file.tar",
    ],
)
def test_chain_parser_roundtrip(urlpath: str):
    parser = FSSpecChainParser()
    segments = parser.unchain(urlpath, protocol=None, storage_options={})
    rechained, kw = parser.chain(segments)
    assert rechained == urlpath
    assert kw == {}


@pytest.mark.parametrize(
    "urlpath,storage_options",
    [
        ("simplecache::memory://a/b", {"simplecache": {"same_names": True}}),
        ("simplecache::memory://a/b", {"same_names": True}),
        (
            "simplecache::memory://a/b",
            {"simplecache": {"same_names": True}, "same_names": False},
        ),
        (
            "simplecache::memory://a/b",
            {"simplecache": {"same_names": True}, "memory": {"key": "value"}},
        ),
        ("memory://a/b", {"memory": {"key": "value"}}),
    ],
)
def test_chaining_upath_storage_options_match_fsspec(urlpath, storage_options):
    # fsspec mutates the nested dicts
    fs, _ = url_to_fs(urlpath, **copy.deepcopy(storage_options))
    pth = UPath(urlpath, **copy.deepcopy(storage_options))
    assert dict(pth.storage_options) == fs.storage_options
    assert pth.fs.storage_options == fs.storage_options


def test_chaining_upath_storage_options_not_mutated():
    storage_options = {
        "simplecache": {"same_names": True},
        "same_names": False,
        "memory": {"key": "value"},
    }
    expected = copy.deepcopy(storage_options)
    UPath("simplecache::memory://a/b", **storage_options)
    assert storage_options == expected


def test_read_file_outermost_storage_options(memory_file_urlpath, tmp_path):
    pth = UPath(
        f"simplecache::{memory_file_urlpath}",
        simplecache={"cache_storage": str(tmp_path)},
    )
    assert pth.read_bytes() == b"hello world"
    assert list(tmp_path.iterdir())


def test_chain_parser_storage_options():
    parser = FSSpecChainParser()
    segments = parser.unchain(
        "zip://file.txt::memory:///tmp.zip",
        protocol=None,
        storage_options={"zip": {"mode": "r"}, "memory": {"key": "value"}},
    )
    assert [s.storage_options for s in segments] == [
        {"mode": "r"},
        {"key": "value"},
    ]


def test_chain_parser_roundtrip_storage_options():
    parser = FSSpecChainParser()
    segments = parser.unchain(
        "zip://file.txt::memory:///tmp.zip",
        protocol=None,
        storage_options={"zip": {"mode": "r"}, "memory": {"key": "value"}},
    )
    rechained, kw = parser.chain(segments)
    assert parser.unchain(rechained, protocol=None, storage_options=kw) == segments
