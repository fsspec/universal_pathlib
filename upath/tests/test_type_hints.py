"""tests for resolving type hints of the public UPath API at runtime

Tools like pydantic, cattrs, tyro or typer call `typing.get_type_hints()`
on classes and their methods. With `from __future__ import annotations`
all annotations are strings, which get evaluated in the namespace of the
defining module, so every name used in a public annotation needs to be
importable at runtime and not only under `TYPE_CHECKING`.

Not covered on purpose: dunder hooks for optional third-party libraries,
like `__get_pydantic_core_schema__`, keep their annotations unresolvable
to avoid importing those libraries at runtime.
"""

import ast
import builtins
import inspect
import re
import subprocess
import sys
import typing

import pytest

from upath import UPath
from upath.extensions import ProxyUPath
from upath.implementations.cloud import CloudPath
from upath.implementations.local import LocalPath
from upath.implementations.local import PosixUPath
from upath.implementations.local import WindowsUPath
from upath.registry import available_implementations
from upath.registry import get_upath_class
from upath.types import storage_options

try:
    import typing_extensions  # noqa: F401
except ImportError:
    HAS_TYPING_EXTENSIONS = False
else:
    HAS_TYPING_EXTENSIONS = True


def _upath_classes():
    classes = {UPath, CloudPath, LocalPath, PosixUPath, WindowsUPath, ProxyUPath}
    for protocol in available_implementations():
        cls = get_upath_class(protocol)
        if cls is not None and cls.__module__.startswith("upath."):
            classes.add(cls)
    return sorted(classes, key=lambda c: f"{c.__module__}.{c.__qualname__}")


def _public_members(cls):
    """yield (name, function) for public methods and property getters"""
    for name in dir(cls):
        if name.startswith("_") and name not in {"__init__", "__new__"}:
            continue
        for base in cls.__mro__:
            if name in base.__dict__:
                break
        else:
            continue
        if not base.__module__.startswith("upath"):
            # members inherited from stdlib pathlib or pathlib_abc
            continue
        attr = base.__dict__[name]
        if isinstance(attr, property):
            func = attr.fget
        elif isinstance(attr, (classmethod, staticmethod)):
            func = attr.__func__
        elif inspect.isfunction(attr):
            func = attr
        else:
            continue
        yield name, func


def _annotation_namespaces(obj):
    """yield (globalns, annotations) like typing.get_type_hints does"""
    if isinstance(obj, type):
        for base in reversed(obj.__mro__):
            module = sys.modules.get(base.__module__)
            annotations = base.__dict__.get("__annotations__", {})
            yield getattr(module, "__dict__", {}), annotations
    else:
        yield obj.__globals__, obj.__annotations__


def _assert_annotation_names_defined(obj):
    for globalns, annotations in _annotation_namespaces(obj):
        for annotation in annotations.values():
            if isinstance(annotation, typing.ForwardRef):
                annotation = annotation.__forward_arg__
            if not isinstance(annotation, str):
                continue
            for node in ast.walk(ast.parse(annotation, mode="eval")):
                if isinstance(node, ast.Name) and not (
                    node.id in globalns or hasattr(builtins, node.id)
                ):
                    raise NameError(f"name {node.id!r} is not defined")


def _get_type_hints(obj):
    try:
        try:
            return typing.get_type_hints(obj)
        except TypeError as err:
            # PEP 604 unions (X | Y) can only be evaluated at runtime on
            # Python 3.10+, so on older versions check that all names resolve
            if sys.version_info >= (3, 10) or "for |" not in str(err):
                raise
            _assert_annotation_names_defined(obj)
    except NameError as err:
        match = re.search(r"name '(\w+)' is not defined", str(err))
        if (
            sys.version_info < (3, 11)
            and not HAS_TYPING_EXTENSIONS
            and match
            and match.group(1) in {"Self", "Unpack"}
        ):
            pytest.skip("Self and Unpack require typing_extensions on Python < 3.11")
        raise


_CASES = [
    pytest.param(func, id=f"{cls.__qualname__}.{name}")
    for cls in _upath_classes()
    for name, func in _public_members(cls)
]


def test_public_members_are_collected():
    ids = {p.id for p in _CASES}
    assert {
        "UPath.__init__",
        "UPath.joinpath",
        "UPath.fs",
        "UPath.copy",
        "S3Path.__init__",
        "PosixUPath.__new__",
        "ProxyUPath.with_segments",
    } <= ids


@pytest.mark.parametrize("func", _CASES)
def test_get_type_hints_public_members(func):
    _get_type_hints(func)


@pytest.mark.parametrize("cls", _upath_classes(), ids=lambda c: c.__qualname__)
def test_get_type_hints_class(cls):
    _get_type_hints(cls)


@pytest.mark.parametrize("name", storage_options.__all__)
def test_get_type_hints_storage_options(name):
    _get_type_hints(getattr(storage_options, name))


def test_import_without_typing_extensions():
    # typing_extensions is not a runtime dependency of universal_pathlib
    code = "\n".join(
        [
            "import sys",
            "sys.modules['typing_extensions'] = None",
            "import upath.extensions",
            "import upath.types.storage_options",
            "from upath.registry import available_implementations",
            "from upath.registry import get_upath_class",
            "for protocol in available_implementations():",
            "    get_upath_class(protocol)",
        ]
    )
    subprocess.run([sys.executable, "-c", code], check=True)
