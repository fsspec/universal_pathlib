import os
from pathlib import PosixPath
from pathlib import WindowsPath

import pytest

from upath import UnsupportedOperation
from upath import UPath
from upath.implementations.local import PosixUPath
from upath.implementations.local import WindowsUPath


def test_provides_unsupportedoperation():
    assert issubclass(UnsupportedOperation, NotImplementedError)


_win_only = pytest.mark.skipif(os.name != "nt", reason="windows only")
_posix_only = pytest.mark.skipif(os.name == "nt", reason="posix only")


@pytest.mark.parametrize(
    "wrong_cls",
    [
        pytest.param(PosixPath, marks=_win_only),
        pytest.param(PosixUPath, marks=_win_only),
        pytest.param(WindowsPath, marks=_posix_only),
        pytest.param(WindowsUPath, marks=_posix_only),
    ],
)
def test_unsupportedoperation_catches_pathlib_errors(wrong_cls):
    with pytest.raises(UnsupportedOperation):
        wrong_cls(".")


@pytest.fixture(params=["", "file", "memory"])
def pth(request, tmp_path):
    pth = UPath(tmp_path, protocol=request.param)
    pth.touch()
    yield pth


def test_signature_stat_follow_symlinks(pth):
    _ = pth.stat(follow_symlinks=True)
