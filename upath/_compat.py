from __future__ import annotations

import sys
import warnings
from functools import wraps
from typing import Any
from typing import Callable
from typing import TypeVar

__all__ = [
    "str_remove_prefix",
    "str_remove_suffix",
    "deprecated",
    "make_instance",
]


if sys.version_info >= (3, 9):
    str_remove_suffix = str.removesuffix
    str_remove_prefix = str.removeprefix

else:

    def str_remove_suffix(s: str, suffix: str) -> str:
        if s.endswith(suffix):
            return s[: -len(suffix)]
        else:
            return s

    def str_remove_prefix(s: str, prefix: str) -> str:
        if s.startswith(prefix):
            return s[len(prefix) :]
        else:
            return s


C = TypeVar("C")


def make_instance(cls: type[C], args: tuple[Any, ...], kwargs: dict[str, Any]) -> C:
    """helper for pickling UPath instances"""
    return cls(*args, **kwargs)


RT = TypeVar("RT")
F = Callable[..., RT]


def deprecated(*, python_version: tuple[int, ...]) -> Callable[[F], F]:
    """marks function as deprecated"""
    pyver_str = ".".join(map(str, python_version))

    def deprecated_decorator(func: F) -> F:
        if sys.version_info >= python_version:

            @wraps(func)
            def wrapper(*args, **kwargs):
                warnings.warn(
                    f"{func.__name__} is deprecated on py>={pyver_str}",
                    DeprecationWarning,
                    stacklevel=2,
                )
                return func(*args, **kwargs)

            return wrapper

        else:
            return func

    return deprecated_decorator
