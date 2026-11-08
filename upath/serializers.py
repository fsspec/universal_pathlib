"""upath.serializers module: convert UPath instances to and from dictionaries

The dictionary format (`SerializedUPath`) contains the `path`, `protocol` and
`storage_options` of a UPath instance. It's the same format that UPath's
pydantic integration uses, so it can be used wherever no automatic integration
exists, e.g. as `json_encoders` in pydantic v1 models.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from typing import TypedDict

from upath.core import UPath

__all__ = [
    "SerializedUPath",
    "upath_from_dict",
    "upath_to_dict",
]


class _SerializedUPathRequired(TypedDict):
    path: str


class SerializedUPath(_SerializedUPathRequired, total=False):
    """Serialized representation of a UPath instance

    `upath_to_dict` always returns all keys. When deserializing via
    `upath_from_dict`, `protocol` and `storage_options` are optional.
    A missing (or `None`) protocol is inferred from the path.
    """

    protocol: str
    storage_options: dict[str, Any]


_SERIALIZED_UPATH_KEYS = frozenset({"path", "protocol", "storage_options"})


def upath_to_dict(path: UPath) -> SerializedUPath:
    """Serialize a UPath instance to a dictionary

    The returned dictionary contains the `path`, `protocol` and
    `storage_options` of the UPath instance. Note that it is only JSON
    serializable if all storage_options values are JSON serializable.

    Parameters
    ----------
    path:
        The UPath instance to serialize.

    Returns
    -------
    SerializedUPath
        A dictionary that can be turned back into an equivalent UPath
        instance via `upath_from_dict`.
    """
    if not isinstance(path, UPath):
        raise TypeError(f"expected a UPath instance, got {type(path).__name__!r}")
    return {
        "path": path.path,
        "protocol": path.protocol,
        "storage_options": dict(path.storage_options),
    }


def upath_from_dict(
    data: Mapping[str, Any],
    *,
    cls: type[UPath] = UPath,
) -> UPath:
    """Create a UPath instance from a serialized dictionary

    Parameters
    ----------
    data:
        A mapping in the `SerializedUPath` format, i.e. with a required
        `path` key and optional `protocol` and `storage_options` keys.
    cls:
        The class to instantiate. Defaults to `UPath`, which returns the
        UPath subclass registered for the protocol.

    Returns
    -------
    UPath
        The deserialized UPath instance.

    Raises
    ------
    TypeError
        If `data` is not a mapping or one of its values has an invalid type.
    ValueError
        If the `path` key is missing or `data` contains unknown keys.
    """
    if not isinstance(data, Mapping):
        raise TypeError(f"expected a mapping, got {type(data).__name__!r}")
    if "path" not in data:
        raise ValueError("serialized UPath is missing the required 'path' key")
    if unknown_keys := data.keys() - _SERIALIZED_UPATH_KEYS:
        unknown = ", ".join(sorted(map(repr, unknown_keys)))
        raise ValueError(f"serialized UPath has unknown keys: {unknown}")

    path = data["path"]
    if not isinstance(path, str):
        raise TypeError(f"'path' must be a str, got {type(path).__name__!r}")

    protocol = data.get("protocol")
    if protocol is not None and not isinstance(protocol, str):
        raise TypeError(
            f"'protocol' must be a str or None, got {type(protocol).__name__!r}"
        )

    storage_options = data.get("storage_options", {})
    if not isinstance(storage_options, Mapping):
        raise TypeError(
            "'storage_options' must be a mapping,"
            f" got {type(storage_options).__name__!r}"
        )
    if not all(isinstance(key, str) for key in storage_options):
        raise TypeError("'storage_options' keys must be str")

    return cls(path, protocol=protocol, **storage_options)
