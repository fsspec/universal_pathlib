import operator
import sys
from contextlib import contextmanager

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
    ver_str = get_package_version_without_import(module)
    if ver_str is None:
        return pytest.mark.skip(reason=f"NOT INSTALLED ({reason})")
    ver = Version(ver_str)
    if not set(conditions).issubset({"lt", "le", "ne", "eq", "ge", "gt"}):
        raise ValueError("unknown condition")
    cond = True
    for op, val in conditions.items():
        cond &= getattr(operator, op)(ver, Version(val))
    return pytest.mark.xfail(cond, reason=reason)


def xfail_if_no_ssl_connection(func):
    try:
        import requests
    except ImportError:
        return pytest.mark.skip(reason="requests not installed")(func)
    try:
        requests.get("https://example.com")
    except (requests.exceptions.ConnectionError, requests.exceptions.SSLError):
        return pytest.mark.xfail(reason="No SSL connection")(func)
    else:
        return func


@contextmanager
def temporary_register(protocol, cls):
    """helper to temporarily register a protocol for testing purposes"""
    from upath.registry import _registry
    from upath.registry import get_upath_class

    m = _registry._m.maps[0]
    try:
        m[protocol] = cls
        yield
    finally:
        m.clear()
        get_upath_class.cache_clear()
