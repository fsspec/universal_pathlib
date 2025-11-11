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


def test_signature_write_text_newline(pth):
    _ = pth.write_text("test", newline="\n")


def test_signature_chmod_follow_symlinks(pth):
    _ = pth.chmod(0o777, follow_symlinks=True)


def test_signature_match_pathlike(pth):
    _ = pth.match(UPath("*.py"))


def test_signature_match_case_sensitive(pth):
    _ = pth.match("*.py", case_sensitive=True)


def test_signature_exists_follow_symlinks(pth):
    _ = pth.exists(follow_symlinks=True)


def test_signature_glob_case_sensitive(pth):
    _ = list(pth.parent.glob("*", case_sensitive=True))


def test_signature_rglob_case_sensitive(pth):
    _ = list(pth.parent.rglob("*", case_sensitive=True))


def test_signature_relative_to_walk_up(pth):
    _ = pth.relative_to(pth.parent.parent, walk_up=False)


def test_signature_is_file_follow_symlinks(pth):
    _ = pth.is_file(follow_symlinks=True)


def test_signature_is_dir_follow_symlinks(pth):
    _ = pth.is_dir(follow_symlinks=True)


def test_signature_read_text_newline(pth):
    pth.write_text("test")
    _ = pth.read_text(newline="\n")


def test_signature_glob_recurse_symlinks(pth):
    _ = list(pth.parent.glob("**/*.py", recurse_symlinks=True))


def test_signature_glob_pathlike(pth):
    _ = list(pth.parent.glob(UPath("**/*.py")))


def test_signature_rglob_recurse_symlinks(pth):
    _ = list(pth.parent.rglob("*.py", recurse_symlinks=True))


def test_signature_rglob_pathlike(pth):
    _ = list(pth.parent.rglob(UPath("*.py")))


def test_signature_owner_follow_symlinks(pth):
    _ = pth.owner(follow_symlinks=True)


def test_signature_group_follow_symlinks(pth):
    _ = pth.group(follow_symlinks=True)
