import pytest

from upath import UPath
from upath.implementations.local import LocalPath, PosixUPath
from upath.tests.cases import BaseTests
from upath.tests.utils import xfail_if_version


class TestFSSpecLocal(BaseTests):
    @pytest.fixture(autouse=True)
    def path(self, local_testdir):
        path = f"file://{local_testdir}"
        self.path = UPath(path)

    def test_is_LocalPath(self):
        assert isinstance(self.path, LocalPath)

    def test_relative_to(self):
        rel_path = UPath("file:///test_bucket/file.txt").relative_to(UPath("file:///test_bucket"))
        assert isinstance(rel_path, PosixUPath)
        assert not rel_path.is_absolute()
        assert 'file.txt' == rel_path.path 

        walk_path = UPath("file:///test_bucket/file.txt").relative_to(UPath("file:///other_test_bucket"), walk_up=True)
        assert isinstance(walk_path, PosixUPath)
        assert not walk_path.is_absolute()
        assert '../test_bucket/file.txt' == walk_path.path

        with pytest.raises(ValueError):
            UPath("file:///test_bucket/file.txt").relative_to(UPath("file:///prod_bucket"))

        with pytest.raises(ValueError):
            UPath("file:///test_bucket/file.txt").relative_to(UPath("s3:///test_bucket"))



@xfail_if_version("fsspec", lt="2023.10.0", reason="requires fsspec>=2023.10.0")
class TestRayIOFSSpecLocal(BaseTests):
    @pytest.fixture(autouse=True)
    def path(self, local_testdir):
        path = f"local://{local_testdir}"
        self.path = UPath(path)

    def test_is_LocalPath(self):
        assert isinstance(self.path, LocalPath)
