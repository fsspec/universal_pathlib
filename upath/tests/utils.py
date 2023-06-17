import sys

import pytest


def skip_on_windows(func):
    return pytest.mark.skipif(
        sys.platform.startswith("win"), reason="Don't run on Windows"
    )(func)


def only_on_windows(func):
    return pytest.mark.skipif(
        not sys.platform.startswith("win"), reason="Only run on Windows"
    )(func)


def posixify(path):
    return str(path).replace("\\", "/")
