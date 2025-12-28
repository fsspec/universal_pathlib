import os
from pathlib import Path

import pytest

from upath import UPath
from upath.implementations.local import LocalPath

from ..cases import BaseTests
from ..utils import OverrideMeta
from ..utils import overrides_base
from ..utils import xfail_if_version


class TestFSSpecLocal(BaseTests, metaclass=OverrideMeta):
    @pytest.fixture(autouse=True)
    def path(self, local_testdir):
        path = f"file://{local_testdir}"
        self.path = UPath(path)

    @overrides_base
    def test_is_correct_class(self):
        assert isinstance(self.path, LocalPath)

    @overrides_base
    def test_cwd(self):
        # .cwd() is implemented for local filesystems
        cwd = type(self.path).cwd()
        assert isinstance(cwd, LocalPath)
        assert cwd.path == Path.cwd().as_posix()

    @overrides_base
    def test_home(self):
        # .home() is implemented for local filesystems
        cwd = type(self.path).home()
        assert isinstance(cwd, LocalPath)
        assert cwd.path == Path.home().as_posix()

    @overrides_base
    def test_chmod(self):
        # .chmod() works for local filesystems
        self.path.joinpath("file1.txt").chmod(777)


@xfail_if_version("fsspec", lt="2023.10.0", reason="requires fsspec>=2023.10.0")
class TestRayIOFSSpecLocal(TestFSSpecLocal):
    @pytest.fixture(autouse=True)
    def path(self, local_testdir):
        path = f"local://{local_testdir}"
        self.path = UPath(path)


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
