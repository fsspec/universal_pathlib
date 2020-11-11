import pytest

import fsspec
from fsspec.spec import AbstractFileSystem
from fsspec.registry import (
    register_implementation,
    known_implementations,
    _registry
)


class DummyTestFS(AbstractFileSystem):
    protocol = "mock"
    _fs_contents = (
        {"name": "top_level", "type": "directory"},
        {"name": "top_level/second_level", "type": "directory"},
        {"name": "top_level/second_level/date=2019-10-01", "type": "directory"},
        {
            "name": "top_level/second_level/date=2019-10-01/a.parquet",
            "type": "file",
            "size": 100,
        },
        {
            "name": "top_level/second_level/date=2019-10-01/b.parquet",
            "type": "file",
            "size": 100,
        },
        {"name": "top_level/second_level/date=2019-10-02", "type": "directory"},
        {
            "name": "top_level/second_level/date=2019-10-02/a.parquet",
            "type": "file",
            "size": 100,
        },
        {"name": "top_level/second_level/date=2019-10-04", "type": "directory"},
        {
            "name": "top_level/second_level/date=2019-10-04/a.parquet",
            "type": "file",
            "size": 100,
        },
        {"name": "misc", "type": "directory"},
        {"name": "misc/foo.txt", "type": "file", "size": 100},
        {"name": "glob_test/hat/^foo.txt", "type": "file", "size": 100},
        {"name": "glob_test/dollar/$foo.txt", "type": "file", "size": 100},
        {"name": "glob_test/lbrace/{foo.txt", "type": "file", "size": 100},
        {"name": "glob_test/rbrace/}foo.txt", "type": "file", "size": 100},
    )

    def __getitem__(self, name):
        for item in self._fs_contents:
            if item["name"] == name:
                return item
        raise IndexError("{name} not found!".format(name=name))

    def ls(self, path, detail=True, **kwargs):
        path = self._strip_protocol(path)

        files = {
            file["name"]: file
            for file in self._fs_contents
            if path == self._parent(file["name"])
        }

        if detail:
            return [files[name] for name in sorted(files)]

        return list(sorted(files))



@pytest.fixture(scope='function')
def clear_registry():
    register_implementation("mock", DummyTestFS)
    try:
        yield
    finally:
        _registry.clear()


@pytest.fixture(scope='function')
def afs(clear_registry):
    
    return
