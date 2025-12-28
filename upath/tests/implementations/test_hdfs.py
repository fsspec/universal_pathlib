"""see upath/tests/conftest.py for fixtures"""

import pytest  # noqa: F401

from upath import UPath
from upath.implementations.hdfs import HDFSPath

from ..cases import BaseTests
from ..utils import OverrideMeta
from ..utils import overrides_base


@pytest.mark.hdfs
class TestUPathHDFS(BaseTests, metaclass=OverrideMeta):
    @pytest.fixture(autouse=True)
    def path(self, local_testdir, hdfs):
        host, user, port = hdfs
        path = f"hdfs:{local_testdir}"
        self.path = UPath(path, host=host, user=user, port=port)

    @overrides_base
    def test_is_correct_class(self):
        assert isinstance(self.path, HDFSPath)
