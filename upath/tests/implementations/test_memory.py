import sys
import pytest

from upath import UPath
from upath.implementations.memory import MemoryPath
from upath.tests.cases import BaseTests


class TestMemoryPath(BaseTests):
    @pytest.fixture(autouse=True)
    def path(self, local_testdir):
        path = f"memory:/{local_testdir}"
        self.path = UPath(path)
        self.prepare_file_system()

    def test_is_MemoryPath(self):
        assert isinstance(self.path, MemoryPath)

    def test_glob(self, pathlib_base):
        mock_glob = list(self.path.glob("**.txt"))
        path_glob = list(pathlib_base.glob("**/*.txt"))

        assert len(mock_glob) == len(path_glob)
        if not sys.platform.startswith("win"):  # need to fix windows tests here
            assert all(
                map(
                    lambda m: m.path in [str(p)[4:] for p in path_glob],
                    mock_glob,
                )
            )
