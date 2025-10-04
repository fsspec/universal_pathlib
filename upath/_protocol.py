from __future__ import annotations

import re
from collections import ChainMap
from pathlib import PurePath
from typing import TYPE_CHECKING
from typing import Any

from fsspec.registry import known_implementations as _known_implementations
from fsspec.registry import registry as _registry

if TYPE_CHECKING:
    from upath.types import JoinablePathLike

__all__ = [
    "get_upath_protocol",
    "normalize_empty_netloc",
    "compatible_protocol",
]

# Regular expression to match fsspec style protocols.
# Matches single slash usage too for compatibility.
_PROTOCOL_RE = re.compile(
    r"^(?P<protocol>[A-Za-z][A-Za-z0-9+]+):(?:(?P<slashes>//?)|:)(?P<path>.*)"
)

# Matches data URIs
_DATA_URI_RE = re.compile(r"^data:[^,]*,")


def _match_protocol(pth: str) -> str:
    if m := _PROTOCOL_RE.match(pth):
        return m.group("protocol")
    elif _DATA_URI_RE.match(pth):
        return "data"
    return ""


_fsspec_registry_map = ChainMap(_registry, _known_implementations)


def _fsspec_protocol_equals(p0: str, p1: str) -> bool:
    """check if two fsspec protocols are equivalent"""
    p0 = p0 or "file"
    p1 = p1 or "file"
    if p0 == p1:
        return True

    try:
        o0 = _fsspec_registry_map[p0]
    except KeyError:
        raise ValueError(f"Protocol not known: {p0!r}")
    try:
        o1 = _fsspec_registry_map[p1]
    except KeyError:
        raise ValueError(f"Protocol not known: {p1!r}")

    return o0 == o1


def get_upath_protocol(
    pth: JoinablePathLike,
    *,
    protocol: str | None = None,
    storage_options: dict[str, Any] | None = None,
) -> str:
    """return the filesystem spec protocol"""
    from upath.core import UPath

    if isinstance(pth, str):
        pth_protocol = _match_protocol(pth)
    elif isinstance(pth, UPath):
        pth_protocol = pth.protocol
    elif isinstance(pth, PurePath):
        pth_protocol = getattr(pth, "protocol", "")
    elif hasattr(pth, "__vfspath__"):
        pth_protocol = _match_protocol(pth.__vfspath__())
    elif hasattr(pth, "__fspath__"):
        pth_protocol = _match_protocol(pth.__fspath__())
    else:
        pth_protocol = _match_protocol(str(pth))
    # if storage_options and not protocol and not pth_protocol:
    #     protocol = "file"
    if protocol is None:
        return pth_protocol or ""
    elif (
        protocol
        and pth_protocol
        and not _fsspec_protocol_equals(pth_protocol, protocol)
    ):
        raise ValueError(
            f"requested protocol {protocol!r} incompatible with {pth_protocol!r}"
        )
    elif protocol == "" and pth_protocol:
        # explicitly requested empty protocol, but path has non-empty protocol
        raise ValueError(
            f"explicitly requested empty protocol {protocol!r}"
            f" incompatible with {pth_protocol!r}"
        )
    return protocol or pth_protocol or ""


def normalize_empty_netloc(pth: str) -> str:
    if m := _PROTOCOL_RE.match(pth):
        if m.group("slashes") == "/":
            protocol = m.group("protocol")
            path = m.group("path")
            pth = f"{protocol}:///{path}"
    return pth


def compatible_protocol(
    protocol: str,
    *args: JoinablePathLike,
) -> bool:
    """check if UPath protocols are compatible"""
    from upath.core import UPath

    for arg in args:
        if isinstance(arg, UPath) and not arg.is_absolute():
            # relative UPath are always compatible
            continue
        other_protocol = get_upath_protocol(arg)
        # consider protocols equivalent if they match up to the first "+"
        other_protocol = other_protocol.partition("+")[0]
        # protocols: only identical (or empty "") protocols can combine
        if other_protocol and not _fsspec_protocol_equals(other_protocol, protocol):
            return False
    return True
