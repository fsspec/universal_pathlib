import pytest

from upath import UPath
from upath.implementations.memory import MemoryPath

from ..cases import BaseTests


class TestMemoryPath(BaseTests):
    @pytest.fixture(autouse=True)
    def path(self, local_testdir):
        if not local_testdir.startswith("/"):
            local_testdir = "/" + local_testdir
        path = f"memory:{local_testdir}"
        self.path = UPath(path)
        self.prepare_file_system()

    def test_is_MemoryPath(self):
        assert isinstance(self.path, MemoryPath)


@pytest.mark.parametrize(
    "path, expected",
    [
        ("memory:/", "memory://"),
        ("memory:/a", "memory://a"),
        ("memory:/a/b", "memory://a/b"),
        ("memory://", "memory://"),
        ("memory://a", "memory://a"),
        ("memory://a/b", "memory://a/b"),
        ("memory:///", "memory://"),
        ("memory:///a", "memory://a"),
        ("memory:///a/b", "memory://a/b"),
    ],
)
def test_string_representation(path, expected):
    path = UPath(path)
    assert str(path) == expected
