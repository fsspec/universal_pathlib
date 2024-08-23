import os
from datetime import datetime
from datetime import timezone

import pytest

import upath


@pytest.fixture
def pth_file(tmp_path):
    f = tmp_path.joinpath("abc.txt")
    f.write_bytes(b"a")
    p = upath.UPath(f"file://{f.absolute().as_posix()}")
    yield p


def test_stat_repr(pth_file):
    assert repr(pth_file.stat()).startswith("UPathStatResult")


def test_stat_as_info(pth_file):
    dct = pth_file.stat().as_info()
    assert dct["size"] == pth_file.stat().st_size


def test_stat_atime(pth_file):
    atime = pth_file.stat().st_atime
    assert isinstance(atime, (float, int))


@pytest.mark.xfail(reason="fsspec does not return 'atime'")
def test_stat_atime_value(pth_file):
    atime = pth_file.stat().st_atime
    assert atime > 0


def test_stat_mtime(pth_file):
    mtime = pth_file.stat().st_mtime
    assert isinstance(mtime, (float, int))


def test_stat_mtime_value(pth_file):
    mtime = pth_file.stat().st_mtime
    assert mtime > 0


def test_stat_ctime(pth_file):
    ctime = pth_file.stat().st_ctime
    assert isinstance(ctime, (float, int))


@pytest.mark.xfail(reason="fsspec returns 'created' but not 'ctime'")
def test_stat_ctime_value(pth_file):
    ctime = pth_file.stat().st_ctime
    assert ctime > 0


def test_stat_birthtime(pth_file):
    birthtime = pth_file.stat().st_birthtime
    assert isinstance(birthtime, (float, int))


def test_stat_birthtime_value(pth_file):
    birthtime = pth_file.stat().st_birthtime
    assert birthtime > 0


def test_stat_seq_interface(pth_file):
    assert len(tuple(pth_file.stat())) == os.stat_result.n_sequence_fields
    assert isinstance(pth_file.stat().index(0), int)
    assert isinstance(pth_file.stat().count(0), int)
    assert isinstance(pth_file.stat()[0], int)


def test_stat_warn_if_dict_interface(pth_file):
    with pytest.warns(DeprecationWarning):
        pth_file.stat().keys()

    with pytest.warns(DeprecationWarning):
        pth_file.stat().items()

    with pytest.warns(DeprecationWarning):
        pth_file.stat().values()

    with pytest.warns(DeprecationWarning):
        pth_file.stat().get("size")

    with pytest.warns(DeprecationWarning):
        pth_file.stat().copy()

    with pytest.warns(DeprecationWarning):
        _ = pth_file.stat()["size"]


@pytest.mark.parametrize(
    "timestamp",
    [
        10,
        datetime(1970, 1, 1, 0, 0, 10, tzinfo=timezone.utc),
        "1970-01-01T00:00:10Z",
        "1970-01-01T00:00:10+00:00",
    ],
)
def test_timestamps(timestamp):
    from upath._stat import UPathStatResult

    s = UPathStatResult(
        [0] * 10,
        {
            "ctime": timestamp,
            "atime": timestamp,
            "mtime": timestamp,
            "created": timestamp,
        },
    )
    assert s.st_atime == 10.0
    assert s.st_ctime == 10.0
    assert s.st_mtime == 10.0


def test_bad_timestamp():
    from upath._stat import UPathStatResult

    with pytest.raises(TypeError), pytest.warns(
        RuntimeWarning, "universal_pathlib/issues"
    ):
        s = UPathStatResult([0] * 10, {"ctime": "bad"})
        _ = s.st_ctime
