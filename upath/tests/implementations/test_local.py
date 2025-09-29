import os
from pathlib import Path

import pytest

from upath import UPath
from upath.implementations.local import LocalPath
from upath.tests.cases import BaseTests
from upath.tests.utils import xfail_if_version


class TestFSSpecLocal(BaseTests):
    @pytest.fixture(autouse=True)
    def path(self, local_testdir):
        path = f"file://{local_testdir}"
        self.path = UPath(path)

    def test_is_LocalPath(self):
        assert isinstance(self.path, LocalPath)

    def test_cwd(self):
        cwd = type(self.path).cwd()
        assert isinstance(cwd, LocalPath)
        assert cwd.path == Path.cwd().as_posix()

    def test_home(self):
        cwd = type(self.path).home()
        assert isinstance(cwd, LocalPath)
        assert cwd.path == Path.home().as_posix()


@xfail_if_version("fsspec", lt="2023.10.0", reason="requires fsspec>=2023.10.0")
class TestRayIOFSSpecLocal(BaseTests):
    @pytest.fixture(autouse=True)
    def path(self, local_testdir):
        path = f"local://{local_testdir}"
        self.path = UPath(path)

    def test_is_LocalPath(self):
        assert isinstance(self.path, LocalPath)

    def test_cwd(self):
        cwd = type(self.path).cwd()
        assert isinstance(cwd, LocalPath)
        assert cwd.path == Path.cwd().as_posix()

    def test_home(self):
        cwd = type(self.path).home()
        assert isinstance(cwd, LocalPath)
        assert cwd.path == Path.home().as_posix()


@pytest.mark.parametrize(
    "protocol,path",
    [
        (None, "/tmp/somefile.txt"),
        ("file", "file:///tmp/somefile.txt"),
        ("local", "local:///tmp/somefile.txt"),
    ],
)
def test_local_paths_are_pathlike(protocol, path):
    assert isinstance(UPath(path, protocol=protocol), os.PathLike)
