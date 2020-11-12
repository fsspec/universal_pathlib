import tempfile
import os
import shutil
from pathlib import Path


import pytest
import fsspec
from fsspec.spec import AbstractFileSystem
from fsspec.implementations.local import LocalFileSystem
from fsspec.registry import (
    register_implementation,
    known_implementations,
    _registry
)


class DummyTestFS(LocalFileSystem):
    protocol = "mock"
    # _fs_contents = (
    #     {"name": "top_level", "type": "directory"},
    #     {"name": "top_level/second_level", "type": "directory"},
    #     {"name": "top_level/second_level/date=2019-10-01", "type": "directory"},
    #     {
    #         "name": "top_level/second_level/date=2019-10-01/a.parquet",
    #         "type": "file",
    #         "size": 100,
    #     },
    #     {
    #         "name": "top_level/second_level/date=2019-10-01/b.parquet",
    #         "type": "file",
    #         "size": 100,
    #     },
    #     {"name": "top_level/second_level/date=2019-10-02", "type": "directory"},
    #     {
    #         "name": "top_level/second_level/date=2019-10-02/a.parquet",
    #         "type": "file",
    #         "size": 100,
    #     },
    #     {"name": "top_level/second_level/date=2019-10-04", "type": "directory"},
    #     {
    #         "name": "top_level/second_level/date=2019-10-04/a.parquet",
    #         "type": "file",
    #         "size": 100,
    #     },
    #     {"name": "misc", "type": "directory"},
    #     {"name": "misc/foo.txt", "type": "file", "size": 100},
    #     {"name": "glob_test/hat/^foo.txt", "type": "file", "size": 100},
    #     {"name": "glob_test/dollar/$foo.txt", "type": "file", "size": 100},
    #     {"name": "glob_test/lbrace/{foo.txt", "type": "file", "size": 100},
    #     {"name": "glob_test/rbrace/}foo.txt", "type": "file", "size": 100},
    # )

    # def __getitem__(self, name):
    #     for item in self._fs_contents:
    #         if item["name"] == name:
    #             return item
    #     raise IndexError("{name} not found!".format(name=name))

    # def ls(self, path, detail=True, **kwargs):
    #     path = self._strip_protocol(path)

    #     files = {
    #         file["name"]: file
    #         for file in self._fs_contents
    #         if path == self._parent(file["name"])
    #     }

    #     if detail:
    #         return [files[name] for name in sorted(files)]

    #     return list(sorted(files))



@pytest.fixture(scope='session')
def clear_registry():
    register_implementation("mock", DummyTestFS)
    try:
        yield
    finally:
        _registry.clear()


@pytest.fixture()
def testingdir(clear_registry):
    tempdir = tempfile.TemporaryDirectory()
    tempdir = tempdir.name
    tmp = Path(tempdir)
    tmp.mkdir()
    folder1 = tmp.joinpath('folder1')
    folder1.mkdir()
    folder1_files = ['file1.txt', 'file2.txt']
    for f in folder1_files:
        p = folder1.joinpath(f)
        p.touch()
        p.write_text(f)

    file1 = tmp.joinpath('file1.txt')
    file1.touch()
    file1.write_text('hello world')
    file2 = tmp.joinpath('file2.txt')
    file2.touch()
    file2.write_bytes(b'hello world')
    yield tempdir
    shutil.rmtree(tempdir)


    


