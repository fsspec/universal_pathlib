from __future__ import annotations

from typing import TYPE_CHECKING

from upath.registry import get_upath_class

if TYPE_CHECKING:
    from upath import UPath


def __getattr__(name: str) -> type[UPath]:
    if name.startswith("_") and name.endswith("Path"):
        protocol = name[1:-4].lower()
        cls = get_upath_class(protocol, fallback=False)
        assert cls is not None
        return cls
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
