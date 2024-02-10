import os
import platform
import sys

import pytest

from upath import UPath
from upath.implementations.github import GitHubPath
from upath.tests.cases import BaseTests

pytestmark = pytest.mark.skipif(
    os.environ.get("CI")
    and (sys.version_info not in {(3, 8), (3, 12)} and platform.system() != "Linux"),
    reason="Skipping GitHubPath tests to prevent rate limiting on GitHub API.",
)


class TestUPathGitHubPath(BaseTests):
    """
    Unit-tests for the GitHubPath implementation of UPath.
    """

    @pytest.fixture(autouse=True)
    def path(self):
        """
        Fixture for the UPath instance to be tested.
        """
        path = "github://ap--:universal_pathlib@test_data/data"
        self.path = UPath(path)

    def test_is_GitHubPath(self):
        """
        Test that the path is a GitHubPath instance.
        """
        assert isinstance(self.path, GitHubPath)

    @pytest.mark.skip(reason="GitHub filesystem is read-only")
    def test_mkdir(self):
        pass

    @pytest.mark.skip(reason="GitHub filesystem is read-only")
    def test_mkdir_exists_ok_false(self):
        pass

    @pytest.mark.skip(reason="GitHub filesystem is read-only")
    def test_mkdir_parents_true_exists_ok_false(self):
        pass

    @pytest.mark.skip(reason="GitHub filesystem is read-only")
    def test_rename(self):
        pass

    @pytest.mark.skip(reason="GitHub filesystem is read-only")
    def test_rename2(self):
        pass

    @pytest.mark.skip(reason="GitHub filesystem is read-only")
    def test_touch_unlink(self):
        pass

    @pytest.mark.skip(reason="GitHub filesystem is read-only")
    def test_write_bytes(self):
        pass

    @pytest.mark.skip(reason="GitHub filesystem is read-only")
    def test_write_text(self):
        pass

    @pytest.mark.skip(reason="GitHub filesystem is read-only")
    def test_fsspec_compat(self):
        pass
