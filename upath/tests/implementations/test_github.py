import pytest

from upath import UPath
from upath.implementations.github import GitHubPath
from upath.tests.cases import BaseTests


class TestUPathGitHubPath(BaseTests):
    """
    Unit-tests for the GitHubPath implementation of UPath.
    """

    @pytest.fixture(autouse=True)
    def path(self):
        """
        Fixture for the UPath instance to be tested.
        """
        path = "github://fsspec:universal_pathlib@main"
        self.path = UPath(path)

    def test_is_GitHubPath(self):
        """
        Test that the path is a GitHubPath instance.
        """
        assert isinstance(self.path, GitHubPath)
