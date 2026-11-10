import os
import sys
import warnings
from pathlib import Path

import pytest

from upath import UPath
from upath.implementations.local import LocalPath

from ..cases import BaseTests
from ..utils import OverrideMeta
from ..utils import overrides_base
from ..utils import skip_on_windows
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


@skip_on_windows
def test_local_mkdir_parent_mode(tmp_path):
    umask = os.umask(0)
    try:
        pth = UPath(tmp_path).joinpath("a", "b", "c")
        pth.mkdir(mode=0o700, parents=True, parent_mode=0o750)
    finally:
        os.umask(umask)
    assert pth.stat().st_mode & 0o777 == 0o700
    assert pth.parent.stat().st_mode & 0o777 == 0o750
    assert pth.parent.parent.stat().st_mode & 0o777 == 0o750


def test_local_is_reserved():
    pth = UPath("file.txt")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        assert pth.is_reserved() is False
    if sys.version_info >= (3, 13):
        with pytest.warns(DeprecationWarning):
            pth.is_reserved()
