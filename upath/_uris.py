from __future__ import annotations

import re
from pathlib import PurePath
from typing import TYPE_CHECKING
from typing import Any
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from upath.core import UPathLike

__all__ = [
    "get_upath_protocol",
    "normalize_empty_netloc",
    "compatible_protocol",
    "upath_urijoin",
]

# Regular expression to match fsspec style protocols.
# Matches single slash usage too for compatibility.
_PROTOCOL_RE = re.compile(
    r"^(?P<protocol>[A-Za-z][A-Za-z0-9+]+):(?P<slashes>//?)(?P<path>.*)"
)

# Matches data URIs
_DATA_URI_RE = re.compile(r"^data:[^,]*,")


def _match_protocol(pth: str) -> str:
    if m := _PROTOCOL_RE.match(pth):
        return m.group("protocol")
    elif _DATA_URI_RE.match(pth):
        return "data"
    return ""


def get_upath_protocol(
    pth: UPathLike,
    *,
    protocol: str | None = None,
    storage_options: dict[str, Any] | None = None,
) -> str:
    """return the filesystem spec protocol"""
    if isinstance(pth, str):
        pth_protocol = _match_protocol(pth)
    elif isinstance(pth, PurePath):
        pth_protocol = getattr(pth, "protocol", "")
    elif hasattr(pth, "__fspath__"):
        pth_protocol = _match_protocol(pth.__fspath__())
    else:
        pth_protocol = _match_protocol(str(pth))
    # if storage_options and not protocol and not pth_protocol:
    #     protocol = "file"
    if protocol and pth_protocol and not pth_protocol.startswith(protocol):
        raise ValueError(
            f"requested protocol {protocol!r} incompatible with {pth_protocol!r}"
        )
    return protocol or pth_protocol or ""


def normalize_empty_netloc(pth: str) -> str:
    if m := _PROTOCOL_RE.match(pth):
        if len(m.group("slashes")) == 1:
            protocol = m.group("protocol")
            path = m.group("path")
            pth = f"{protocol}:///{path}"
    return pth


def compatible_protocol(protocol: str, *args: UPathLike) -> bool:
    """check if UPath protocols are compatible"""
    for arg in args:
        other_protocol = get_upath_protocol(arg)
        # consider protocols equivalent if they match up to the first "+"
        other_protocol = other_protocol.partition("+")[0]
        # protocols: only identical (or empty "") protocols can combine
        if other_protocol and other_protocol != protocol:
            return False
    return True


def upath_urijoin(base: str, uri: str) -> str:
    """Join a base URI and a possibly relative URI to form an absolute
    interpretation of the latter."""
    # see:
    #   https://github.com/python/cpython/blob/ae6c01d9d2/Lib/urllib/parse.py#L539-L605
    # modifications:
    #   - removed allow_fragments parameter
    #   - all schemes are considered to allow relative paths
    #   - all schemes are considered to allow netloc (revisit this)
    #   - no bytes support (removes encoding and decoding)
    if not base:
        return uri
    if not uri:
        return base

    bs = urlsplit(base, scheme="")
    us = urlsplit(uri, scheme=bs.scheme)

    if us.scheme != bs.scheme:  # or us.scheme not in uses_relative:
        return uri
    # if us.scheme in uses_netloc:
    if us.netloc:
        return us.geturl()
    else:
        us = us._replace(netloc=bs.netloc)
    # end if
    if not us.path and not us.fragment:
        us = us._replace(path=bs.path, fragment=bs.fragment)
        if not us.query:
            us = us._replace(query=bs.query)
        return us.geturl()

    base_parts = bs.path.split("/")
    if base_parts[-1] != "":
        del base_parts[-1]

    if us.path[:1] == "/":
        segments = us.path.split("/")
    else:
        segments = base_parts + us.path.split("/")
        segments[1:-1] = filter(None, segments[1:-1])

    resolved_path: list[str] = []

    for seg in segments:
        if seg == "..":
            try:
                resolved_path.pop()
            except IndexError:
                pass
        elif seg == ".":
            continue
        else:
            resolved_path.append(seg)

    if segments[-1] in (".", ".."):
        resolved_path.append("")

    return us._replace(path="/".join(resolved_path) or "/").geturl()
