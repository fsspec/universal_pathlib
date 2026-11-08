import os
from pathlib import Path

import pytest

from upath import UPath
from upath.implementations.local import LocalPath

from ..cases import BaseTests
from ..utils import OverrideMeta
from ..utils import only_on_windows
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


@pytest.mark.parametrize("name", ["file.txt", "a b#%é?.txt"])
def test_local_from_uri_roundtrip(tmp_path, name):
    pth = UPath(tmp_path).joinpath(name)
    uri = pth.as_uri()
    assert type(pth).from_uri(uri) == pth
    assert type(type(pth).from_uri(uri)) is type(pth)


@pytest.mark.parametrize("uri", ["s3://bucket/file.txt", "file:relative/file.txt"])
def test_local_from_uri_invalid(uri):
    with pytest.raises(ValueError):
        type(UPath(".")).from_uri(uri)


@only_on_windows
@pytest.mark.parametrize(
    "uri", ["file://server/share/file.txt", "file:////server/share/file.txt"]
)
def test_local_from_uri_unc_paths(uri):
    # https://github.com/fsspec/universal_pathlib/issues/557
    from upath.implementations.local import WindowsUPath

    pth = WindowsUPath.from_uri(uri)
    assert pth == WindowsUPath(r"\\server\share\file.txt")
    assert WindowsUPath.from_uri(pth.as_uri()) == pth


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
