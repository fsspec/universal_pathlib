import pytest

from upath import UPath
from upath.tests.cases import BaseTests
from upath.tests.utils import skip_on_windows
from upath.tests.utils import xfail_if_version

_xfail_old_fsspec = xfail_if_version(
    "fsspec",
    lt="2022.7.0",
    reason="fsspec<2022.7.0 sftp does not support create_parents",
)


@skip_on_windows
class TestUPathSFTP(BaseTests):

    @pytest.fixture(autouse=True)
    def path(self, ssh_fixture):
        self.path = UPath(ssh_fixture)

    @_xfail_old_fsspec
    def test_mkdir(self):
        super().test_mkdir()

    @_xfail_old_fsspec
    def test_mkdir_exists_ok_true(self):
        super().test_mkdir_exists_ok_true()

    @_xfail_old_fsspec
    def test_mkdir_exists_ok_false(self):
        super().test_mkdir_exists_ok_false()

    @_xfail_old_fsspec
    def test_mkdir_parents_true_exists_ok_false(self):
        super().test_mkdir_parents_true_exists_ok_false()

    @_xfail_old_fsspec
    def test_mkdir_parents_true_exists_ok_true(self):
        super().test_mkdir_parents_true_exists_ok_true()


@pytest.mark.parametrize(
    "args,parts",
    [
        (("sftp://user@host",), ("/",)),
        (("sftp://user@host/",), ("/",)),
        (("sftp://user@host", ""), ("/",)),
        (("sftp://user@host/", ""), ("/",)),
        (("sftp://user@host", "/"), ("/",)),
        (("sftp://user@host/", "/"), ("/",)),
        (("sftp://user@host/abc",), ("/", "abc")),
        (("sftp://user@host", "abc"), ("/", "abc")),
        (("sftp://user@host", "/abc"), ("/", "abc")),
        (("sftp://user@host/", "/abc"), ("/", "abc")),
    ],
)
def test_join_produces_correct_parts(args, parts):
    pth = UPath(*args)
    assert pth.storage_options == {"host": "host", "username": "user"}
    assert pth.parts == parts
