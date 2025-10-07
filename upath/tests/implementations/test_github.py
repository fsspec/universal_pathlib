import os
import platform
import sys

import pytest

from upath import UPath
from upath.implementations.github import GitHubPath
from upath.tests.cases import BaseTests

pytestmark = pytest.mark.skipif(
    os.environ.get("CI")
    and not (
        platform.system() == "Linux" and sys.version_info[:2] in {(3, 9), (3, 13)}
    ),
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

    @pytest.fixture(autouse=True)
    def _xfail_on_rate_limit_errors(self):
        try:
            yield
        except Exception as e:
            if "rate limit exceeded" in str(e):
                pytest.xfail("GitHub API rate limit exceeded")
            else:
                raise

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
    def test_touch(self):
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

    @pytest.mark.skip(reason="Only testing read on GithubPath")
    def test_move_local(self, tmp_path):
        pass

    @pytest.mark.skip(reason="Only testing read on GithubPath")
    def test_move_into_local(self, tmp_path):
        pass

    @pytest.mark.skip(reason="Only testing read on GithubPath")
    def test_move_memory(self, clear_fsspec_memory_cache):
        pass

    @pytest.mark.skip(reason="Only testing read on GithubPath")
    def test_move_into_memory(self, clear_fsspec_memory_cache):
        pass
