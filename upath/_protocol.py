from __future__ import annotations

import os
import re
from pathlib import PurePath
from typing import Any

from fsspec.core import strip_protocol as strip_fsspec_protocol
from fsspec.spec import AbstractFileSystem

__all__ = [
    "get_upath_protocol",
    "strip_upath_protocol",
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
    pth: str | PurePath | os.PathLike,
    *,
    protocol: str | None = None,
    storage_options: dict[str, Any] | None = None,
) -> str:
    """return the filesystem spec protocol"""
    if isinstance(pth, str):
        pth_protocol = _match_protocol(pth)
    elif isinstance(pth, PurePath):
        pth_protocol = getattr(pth, "protocol", "")
    else:
        pth_protocol = _match_protocol(str(pth))
    # if storage_options and not protocol and not pth_protocol:
    #     protocol = "file"
    if protocol and pth_protocol and not pth_protocol.startswith(protocol):
        raise ValueError(
            f"requested protocol {protocol!r} incompatible with {pth_protocol!r}"
        )
    return protocol or pth_protocol or ""


def strip_upath_protocol(
    pth: str | os.PathLike[str],
    *,
    allow_unknown: bool = False,
) -> str:
    """strip protocol from path"""
    if isinstance(pth, PurePath):
        pth = str(pth)
    elif not isinstance(pth, str):
        pth = os.fspath(pth)
    if m := _PROTOCOL_RE.match(pth):
        if len(m.group("slashes")) == 1:
            protocol = m.group("protocol")
            path = m.group("path")
            pth = f"{protocol}:///{path}"
        try:
            return strip_fsspec_protocol(pth)
        except ValueError as err:
            if allow_unknown and str(err).endswith(m.group("protocol")):
                # fsspec raised ValueError because the protocol is not registered
                return AbstractFileSystem._strip_protocol(pth)
            raise
    else:
        return pth
