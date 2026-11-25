import functools
import json
import os
import platform
import re
import sys
import urllib.request

import pytest

from upath import UPath
from upath.implementations.github import GitHubPath

from ..cases import JoinablePathTests
from ..cases import NonWritablePathTests
from ..cases import ReadablePathTests
from ..utils import OverrideMeta
from ..utils import overrides_base

pytestmark = [
    pytest.mark.skipif(
        os.environ.get("CI", False)
        and not (
            platform.system() == "Linux" and sys.version_info[:2] in {(3, 9), (3, 13)}
        ),
        reason="Skipping GitHubPath tests to prevent rate limiting on GitHub API.",
    ),
    pytest.mark.network,
]


def github_rate_limit_exhausted() -> bool:
    """Check the GitHub API rate limit (this request doesn't count against it)."""
    try:
        with urllib.request.urlopen(
            "https://api.github.com/rate_limit", timeout=10
        ) as r:
            return json.load(r)["resources"]["core"]["remaining"] == 0
    except Exception:
        return False


# requests: "503 Server Error: ... for url: ...", aiohttp: "503, message='...', url=..."
SERVER_ERROR = re.compile(r"\b5\d\d(?: Server Error:|, message=)")


def xfail_on_github_connection_error(func):
    """Method decorator to xfail tests on GitHub rate limit or connection errors."""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            str_e = str(e)
            lower_e = str_e.lower()
            if "rate limit exceeded" in lower_e or "too many requests" in lower_e:
                pytest.xfail("GitHub API rate limit exceeded")
            elif SERVER_ERROR.search(str_e) and "github" in lower_e:
                pytest.xfail("GitHub server error")
            elif (
                "nodename nor servname provided, or not known" in str_e
                or "Network is unreachable" in str_e
                or "NameResolutionError" in str_e
            ):
                pytest.xfail("No internet connection")
            elif github_rate_limit_exhausted():
                # fsspec's exists() and find() swallow rate limit errors, so
                # tests can fail with missing files instead
                pytest.xfail("GitHub API rate limit exceeded")
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
class TestUPathGitHubPath(
    JoinablePathTests,
    ReadablePathTests,
    NonWritablePathTests,
    metaclass=OverrideMeta,
):
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

    @overrides_base
    def test_is_correct_class(self):
        assert isinstance(self.path, GitHubPath)
