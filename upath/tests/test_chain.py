import os
from pathlib import Path

import pytest
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
                "fo": Path("/tmp").absolute().as_posix(),
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
    segments = parser.unchain(urlpath, {})
    rechained, kw = parser.chain(segments)
    assert rechained == urlpath
    assert kw == {}
