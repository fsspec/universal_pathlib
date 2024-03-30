"""Generates the _flavour_sources.py file"""

from __future__ import annotations

import inspect
import re
import sys
import warnings
from io import StringIO
from typing import Any
from unittest.mock import Mock

from fsspec.registry import available_protocols
from fsspec.registry import get_filesystem_class
from fsspec.spec import AbstractFileSystem
from fsspec.utils import get_package_version_without_import

HEADER = '''\
""" upath._flavour_sources

<experimental!>

Warning
-------
  Do not modify this file manually!
  It is generated by `dev/generate_flavours.py`

To be able to parse the different filesystem uri schemes, we need
the string parsing functionality each of the filesystem implementations.
In an attempt to support parsing uris without having to import the
specific filesystems, we extract the necessary subset of the
AbstractFileSystem classes and generate a new "flavour" class for
each of the known filesystems. This will allow us to provide a
`PurePath` equivalent `PureUPath` for each protocol in the future
without a direct dependency on the underlying filesystem package.

"""
'''

IMPORTS = """\
from __future__ import annotations

import logging
import re
from typing import Any
from typing import Literal
from typing import cast
from urllib.parse import parse_qs
from urllib.parse import urlsplit

from fsspec.implementations.local import make_path_posix
from fsspec.utils import infer_storage_options
from fsspec.utils import stringify_path

"""

INIT_CODE = '''\
__all__ = [
    "AbstractFileSystemFlavour",
    "FileSystemFlavourBase",
    "flavour_registry",
]

logger = logging.getLogger(__name__)
flavour_registry: dict[str, type[FileSystemFlavourBase]] = {}


class FileSystemFlavourBase:
    """base class for the fsspec flavours"""

    protocol: str | tuple[str, ...]
    root_marker: Literal["/", ""]
    sep: Literal["/"]

    @classmethod
    def _strip_protocol(cls, path):
        raise NotImplementedError

    @staticmethod
    def _get_kwargs_from_urls(path):
        raise NotImplementedError

    @classmethod
    def _parent(cls, path):
        raise NotImplementedError

    def __init_subclass__(cls: Any, **kwargs):
        if isinstance(cls.protocol, str):
            protocols = (cls.protocol,)
        else:
            protocols = tuple(cls.protocol)
        for protocol in protocols:
            if protocol in flavour_registry:
                raise ValueError(f"protocol {protocol!r} already registered")
            flavour_registry[protocol] = cls
'''

BASE_CLASS_NAME_SUFFIX = "Flavour"
BASE_CLASS_NAME = f"{AbstractFileSystem.__name__}{BASE_CLASS_NAME_SUFFIX}"

SKIP_PROTOCOLS = [
    "dir",
    "blockcache",
    "cached",
    "simplecache",
    "filecache",
]

FIX_PROTOCOLS = {
    "MemFS": ("memfs",),
    "AsyncLocalFileSystem": (),
}

FIX_METHODS = {
    "GCSFileSystem": ["_strip_protocol", "_get_kwargs_from_urls", "_split_path"],
}


def _fix_abstract_file_system(x: str) -> str:
    x = re.sub(
        "protocol = 'abstract'",
        "protocol: str | tuple[str, ...] = 'abstract'",
        x
    )
    x = re.sub(
        "root_marker = ''",
        "root_marker: Literal['', '/'] = ''",
        x
    )
    x = re.sub(
        "sep = '/'",
        "sep: Literal['/'] = '/'",
        x
    )
    return x


def _fix_azure_blob_file_system(x: str) -> str:
    x = re.sub(
        r"if isinstance\(path, list\):",
        'if isinstance(path, list):  # type: ignore[unreachable]',
        x,
    )
    x = re.sub(
        r"(return \[.*\])",
        r"\1  # type: ignore[unreachable]",
        x,
    )
    return x


def _fix_memfs_file_system(x: str) -> str:
    return re.sub(
        "_MemFS",
        "MemoryFileSystemFlavour",
        x,
    )


def _fix_oss_file_system(x: str) -> str:
    x = re.sub(
        r"path_string: str = stringify_path\(path\)",
        "path_string = stringify_path(path)",
        x,
    )
    return x


def _fix_xrootd_file_system(x: str) -> str:
    x = re.sub(
        r"client.URL",
        "urlsplit",
        x,
    )
    return re.sub(
        "url.hostid",
        "url.netloc",
        x,
    )


FIX_SOURCE = {
    "AbstractFileSystem": _fix_abstract_file_system,
    "AzureBlobFileSystem": _fix_azure_blob_file_system,
    "MemFS": _fix_memfs_file_system,
    "OSSFileSystem": _fix_oss_file_system,
    "XRootDFileSystem": _fix_xrootd_file_system,
}


def before_imports() -> None:
    """allow to patch the generated state before importing anything"""
    # patch libarchive
    sys.modules["libarchive"] = Mock()
    sys.modules["libarchive.ffi"] = Mock()
    # patch xrootd
    sys.modules["XRootD"] = Mock()
    sys.modules["XRootD.client"] = Mock()
    sys.modules["XRootD.client.flags"] = Mock()
    sys.modules["XRootD.client.responses"] = Mock()


def get_protos(cls: type, remove: str, add: str) -> tuple[str, ...]:
    try:
        return FIX_PROTOCOLS[cls.__name__]
    except KeyError:
        pass
    if isinstance(cls.protocol, str):
        p = [cls.protocol, add]
    else:
        p = [*cls.protocol, add]
    return tuple([x for x in p if x != remove])


def get_fsspec_filesystems_and_protocol_errors() -> (
    tuple[dict[type[AbstractFileSystem], tuple[str, ...]], dict[str, str]]
):
    before_imports()

    classes: dict[type[AbstractFileSystem], tuple[str]] = {}
    errors: dict[str, str] = {}

    for protocol in available_protocols():
        if protocol in SKIP_PROTOCOLS:
            continue
        try:
            cls = get_filesystem_class(protocol)
        except ImportError as err:
            errors[protocol] = str(err)
        else:
            protos = get_protos(cls, remove="abstract", add=protocol)
            cprotos = classes.get(cls, [])
            classes[cls] = tuple(dict.fromkeys([*cprotos, *protos]))
    return classes, errors


def _get_plain_method(cls, name):
    for c in cls.__mro__:
        try:
            return c.__dict__[name]
        except KeyError:
            pass
    else:
        raise AttributeError(f"{cls.__name__}.{name} not found")


def get_subclass_methods(cls: type) -> list[str]:  # noqa: C901
    try:
        return FIX_METHODS[cls.__name__]
    except KeyError:
        pass
    errors = []

    # storage options
    so = None
    base_get_kwargs_from_urls = _get_plain_method(
        AbstractFileSystem, "_get_kwargs_from_urls"
    )
    try:
        cls_get_kwargs_from_urls = _get_plain_method(cls, "_get_kwargs_from_urls")
    except AttributeError:
        errors.append("missing `_get_kwargs_from_urls()`")
    else:
        so = cls_get_kwargs_from_urls is base_get_kwargs_from_urls
        if not isinstance(cls_get_kwargs_from_urls, staticmethod):
            warnings.warn(
                f"{cls.__name__}: {cls_get_kwargs_from_urls!r} not a staticmethod",
                RuntimeWarning,
                stacklevel=2,
            )

    # strip protocol
    sp = None
    base_strip_protocol = _get_plain_method(AbstractFileSystem, "_strip_protocol")
    try:
        cls_strip_protocol = _get_plain_method(cls, "_strip_protocol")
    except AttributeError:
        errors.append("missing `_strip_protocol()`")
    else:
        if isinstance(cls_strip_protocol, staticmethod):
            warnings.warn(
                f"{cls.__name__}: {cls_strip_protocol.__name__!r} is not a classmethod",
                UserWarning,
                stacklevel=2,
            )
            sp = False
        elif isinstance(cls_strip_protocol, classmethod):
            sp = cls_strip_protocol.__func__ is base_strip_protocol.__func__
        else:
            errors.append(
                f"{cls.__name__}: {cls_strip_protocol.__name__!r} not a classmethod"
            )

    # _parent
    pt = None
    base_parent = _get_plain_method(AbstractFileSystem, "_parent")
    try:
        cls_parent = _get_plain_method(cls, "_parent")
    except AttributeError:
        errors.append("missing `_parent()`")
    else:
        pt = cls_parent is base_parent

    if errors or sp is None or so is None:
        raise AttributeError(" AND ".join(errors))

    methods = []
    if not sp:
        methods.append("_strip_protocol")
    if not so:
        methods.append("_get_kwargs_from_urls")
    if not pt:
        methods.append("_parent")
    return methods


def generate_class_source_code(
    cls: type,
    methods: list[str],
    overrides: dict[str, Any],
    attributes: list[str],
    cls_suffix: str,
    base_cls: str | None,
) -> str:
    s = ["\n"]
    if base_cls:
        s += [f"class {cls.__name__}{cls_suffix}({base_cls}):"]
    else:
        s += [f"class {cls.__name__}{cls_suffix}:"]
    mod_ver = get_package_version_without_import(cls.__module__.partition(".")[0])
    s.append(f"    __orig_class__ = '{cls.__module__}.{cls.__name__}'")
    s.append(f"    __orig_version__ = {mod_ver!r}")
    for attr, value in overrides.items():
        s.append(f"    {attr} = {value!r}")
    for attr in attributes:
        s.append(f"    {attr} = {getattr(cls, attr)!r}")
    s.append("")
    for method in methods:
        s.append(inspect.getsource(getattr(cls, method)))
    try:
        fix_func = FIX_SOURCE[cls.__name__]
    except KeyError:
        return "\n".join(s)
    else:
        return "\n".join(fix_func(line) for line in s)


def create_source() -> str:
    buf = StringIO()
    buf.write(HEADER)

    classes, errors = get_fsspec_filesystems_and_protocol_errors()

    srcs = [
        generate_class_source_code(
            AbstractFileSystem,
            ["_strip_protocol", "_get_kwargs_from_urls", "_parent"],
            {},
            ["protocol", "root_marker", "sep"],
            cls_suffix=BASE_CLASS_NAME_SUFFIX,
            base_cls="FileSystemFlavourBase",
        )
    ]

    for cls in sorted(classes, key=lambda cls: cls.__name__):
        try:
            sub_cls_methods = get_subclass_methods(cls)
        except AttributeError as err:
            protos = (cls.protocol,) if isinstance(cls.protocol, str) else cls.protocol
            for proto in protos:
                errors[proto] = str(err)
            continue
        sub_cls = generate_class_source_code(
            cls,
            sub_cls_methods,
            {"protocol": classes[cls]},
            ["root_marker", "sep"],
            cls_suffix=BASE_CLASS_NAME_SUFFIX,
            base_cls=BASE_CLASS_NAME,
        )
        srcs.append(sub_cls)

    if SKIP_PROTOCOLS:
        buf.write("#\n# skipping protocols:\n")
        for protocol in sorted(SKIP_PROTOCOLS):
            buf.write(f"#   - {protocol}\n")

    if errors:
        buf.write("# protocol import errors:\n")
        for protocol, error_msg in sorted(errors.items()):
            buf.write(f"#   - {protocol} ({error_msg})\n")
        buf.write("#\n")

    buf.write(IMPORTS)
    buf.write(INIT_CODE)
    for cls_src in srcs:
        buf.write(cls_src)

    return buf.getvalue().removesuffix("\n")


if __name__ == "__main__":
    print(create_source())
