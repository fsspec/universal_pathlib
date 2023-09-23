import operator
import sys

import pytest
from fsspec.utils import get_package_version_without_import
from packaging.version import Version


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


def xfail_if_version(module, *, reason, **conditions):
    ver = Version(get_package_version_without_import(module))
    if not set(conditions).issubset({"lt", "le", "ne", "eq", "ge", "gt"}):
        raise ValueError("unknown condition")
    cond = True
    for op, val in conditions.items():
        cond &= getattr(operator, op)(ver, Version(val))
    return pytest.mark.xfail(cond, reason=reason)
