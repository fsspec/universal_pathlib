import pytest

from upath import UPath
from upath.implementations.sftp import SFTPPath

from ..cases import BaseTests
from ..utils import OverrideMeta
from ..utils import overrides_base
from ..utils import skip_on_windows


@skip_on_windows
class TestUPathSFTP(BaseTests, metaclass=OverrideMeta):

    @pytest.fixture(autouse=True)
    def path(self, ssh_fixture):
        self.path = UPath(ssh_fixture)

    @overrides_base
    def test_is_correct_class(self):
        assert isinstance(self.path, SFTPPath)


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
