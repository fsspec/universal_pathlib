import os
import sys
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
def pth(request, tmp_path, clear_fsspec_memory_cache):
    pth = UPath(tmp_path, protocol=request.param)
    yield pth


@pytest.fixture
def pth_file(pth):
    f = pth.joinpath("testfile")
    f.touch()
    return f


@pytest.mark.parametrize(
    "pth",
    [
        pytest.param(
            "",
            marks=pytest.mark.xfail(
                sys.version_info < (3, 10), reason="parents getitem differs"
            ),
        ),
        "file",
        "memory",
    ],
    indirect=True,
)
def test_signature_parents_getitem(pth):
    pth.parents[-1]
    pth.parents[0:2]


def test_signature_stat_follow_symlinks(pth_file):
    pth_file.stat(follow_symlinks=True)


def test_signature_write_text_newline(pth):
    _ = pth.joinpath("somename").write_text("test", newline="\n")


@pytest.mark.parametrize("pth", ["", "file"], indirect=True)
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
    p0 = pth.joinpath("test")
    p0.write_text("test")
    _ = p0.read_text(newline="\n")


def test_signature_glob_recurse_symlinks(pth):
    _ = list(pth.parent.glob("**/*.py", recurse_symlinks=True))


def test_signature_glob_pathlike(pth):
    _ = list(pth.parent.glob(UPath("**/*.py")))


def test_signature_rglob_recurse_symlinks(pth):
    _ = list(pth.parent.rglob("*.py", recurse_symlinks=True))


def test_signature_rglob_pathlike(pth):
    _ = list(pth.parent.rglob(UPath("*.py")))


@pytest.mark.parametrize("pth", [""], indirect=True)
def test_signature_owner_follow_symlinks(pth):
    _ = pth.owner(follow_symlinks=True)


@pytest.mark.parametrize("pth", [""], indirect=True)
def test_signature_group_follow_symlinks(pth):
    _ = pth.group(follow_symlinks=True)
