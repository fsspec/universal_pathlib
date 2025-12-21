import functools
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


def xfail_on_github_connection_error(func):
    """Method decorator to xfail tests on GitHub rate limit or connection errors."""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            str_e = str(e)
            if "rate limit exceeded" in str_e or "too many requests for url" in str_e:
                pytest.xfail("GitHub API rate limit exceeded")
            elif (
                "nodename nor servname provided, or not known" in str_e
                or "Network is unreachable" in str_e
            ):
                pytest.xfail("No internet connection")
            else:
                raise

    return wrapper


def wrap_all_tests(decorator):
    """Class decorator factory to wrap all test methods with a given decorator."""

    def class_decorator(cls):
        for attr_name in dir(cls):
            if attr_name.startswith("test_"):
                orig_method = getattr(cls, attr_name)
                setattr(cls, attr_name, decorator(orig_method))
        return cls

    return class_decorator


@wrap_all_tests(xfail_on_github_connection_error)
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

    @pytest.mark.skip(reason="Only testing read on GithubPath")
    def test_rename_with_target_absolute(self, target_factory):
        return super().test_rename_with_target_str_absolute(target_factory)
