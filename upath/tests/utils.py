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
        get_upath_class.cache_clear()
        yield
    finally:
        m.clear()
        get_upath_class.cache_clear()


def extends_base(method):
    """Decorator to ensure a method extends the base class and does NOT
    override a method in base classes.

    Use this decorator in implementation-specific test classes to ensure that
    test methods don't accidentally override methods defined in test base classes.

    Example:
        class TestSpecificImpl(TestBaseClass, metaclass=OverrideMeta):
            @extends_base
            def test_something(self):  # Raises TypeError if base has this method
                ...

            @extends_base
            def test_new_method(self):  # This is fine - no override
                ...
    """
    method.__override_check__ = False
    return method


def overrides_base(method):
    """Decorator to ensure a method DOES override a method in base classes.

    Use this decorator in implementation-specific test classes to ensure that
    test methods intentionally override methods defined in test base classes.

    Example:
        class TestSpecificImpl(TestBaseClass, metaclass=OverrideMeta):
            @overrides_base
            def test_something(self):  # Raises TypeError if base lacks this method
                ...

            @overrides_base
            def test_new_method(self):  # Raises TypeError - no method to override
                ...
    """
    method.__override_check__ = True
    return method


class OverrideMeta(type):
    """Metaclass that enforces @extends_base and @overrides_base decorator constraints.

    When a class uses this metaclass:
    - Methods decorated with @extends_base are checked to ensure they don't
      override a method from any base class.
    - Methods decorated with @overrides_base are checked to ensure they do
      override a method from at least one base class.
    """

    def __new__(mcs, name, bases, namespace):
        for attr_name, attr_value in namespace.items():
            if not callable(attr_value):
                continue

            check = getattr(attr_value, "__override_check__", None)
            if check is None:
                continue

            has_in_base = any(hasattr(base, attr_name) for base in bases)

            if check is False and has_in_base:
                base_name = next(b.__name__ for b in bases if hasattr(b, attr_name))
                raise TypeError(
                    f"Method '{attr_name}' in class '{name}' is decorated "
                    f"with @extends_base but overrides a method from base "
                    f"class '{base_name}'"
                )
            elif check is True and not has_in_base:
                raise TypeError(
                    f"Method '{attr_name}' in class '{name}' is decorated "
                    f"with @overrides_base but does not override any method from "
                    f"base classes"
                )

        return super().__new__(mcs, name, bases, namespace)
