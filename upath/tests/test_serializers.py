import json
import pathlib
import typing

import pytest

from upath import UPath
from upath.extensions import ProxyUPath
from upath.serializers import SerializedUPath
from upath.serializers import upath_from_dict
from upath.serializers import upath_to_dict


@pytest.mark.parametrize(
    "path,storage_options",
    [
        (pathlib.Path.cwd().joinpath("my", "path").as_posix(), {}),
        ("file:///my/path", {}),
        ("memory:///my/path", {}),
        ("memory:///my/path", {"foo": "bar", "baz": 3}),
        ("s3://bucket/key", {"anon": True}),
        ("https://www.example.com/a/b", {}),
    ],
)
@pytest.mark.parametrize("via_json", [False, True], ids=["dict", "json"])
def test_roundtrip(path, storage_options, via_json):
    u = UPath(path, **storage_options)

    data = upath_to_dict(u)
    assert data == {
        "path": u.path,
        "protocol": u.protocol,
        "storage_options": dict(u.storage_options),
    }
    if via_json:
        data = json.loads(json.dumps(data))
    loaded = upath_from_dict(data)

    assert type(loaded) is type(u)
    assert loaded.path == u.path
    assert loaded.protocol == u.protocol
    assert loaded.storage_options == u.storage_options


def test_to_dict_returns_plain_storage_options_dict():
    u = UPath("memory:///my/path", foo="bar")

    data = upath_to_dict(u)
    data["storage_options"]["foo"] = "baz"

    assert type(data["storage_options"]) is dict
    assert u.storage_options["foo"] == "bar"


def test_to_dict_proxyupath():
    u = ProxyUPath("memory:///my/path", foo="bar")

    assert upath_to_dict(u) == {
        "path": "/my/path",
        "protocol": "memory",
        "storage_options": {"foo": "bar"},
    }


@pytest.mark.parametrize("obj", ["memory:///my/path", pathlib.PurePath("a"), None])
def test_to_dict_rejects_non_upath(obj):
    with pytest.raises(TypeError, match="expected a UPath instance"):
        upath_to_dict(obj)


@pytest.mark.parametrize(
    "data",
    [
        {"path": "memory:///my/path"},
        {"path": "memory:///my/path", "protocol": None},
        {"path": "/my/path", "protocol": "memory"},
        {"path": "/my/path", "protocol": "memory", "storage_options": {}},
    ],
)
def test_from_dict_optional_keys(data):
    u = upath_from_dict(data)

    assert u.path == "/my/path"
    assert u.protocol == "memory"
    assert dict(u.storage_options) == {}


def test_from_dict_cls():
    data = upath_to_dict(UPath("memory:///my/path", foo="bar"))

    u = upath_from_dict(data, cls=ProxyUPath)  # type: ignore[arg-type]

    assert isinstance(u, ProxyUPath)
    assert u.path == "/my/path"
    assert u.protocol == "memory"
    assert u.storage_options == {"foo": "bar"}


@pytest.mark.parametrize(
    "data,exc,match",
    [
        ("memory:///my/path", TypeError, "expected a mapping"),
        ({}, ValueError, "missing the required 'path' key"),
        ({"protocol": "memory"}, ValueError, "missing the required 'path' key"),
        ({"path": "/a", "unknown": 1}, ValueError, "unknown keys: 'unknown'"),
        ({"path": 1}, TypeError, "'path' must be a str"),
        ({"path": pathlib.PurePath("a")}, TypeError, "'path' must be a str"),
        ({"path": "/a", "protocol": 1}, TypeError, "'protocol' must be a str"),
        ({"path": "/a", "storage_options": None}, TypeError, "must be a mapping"),
        ({"path": "/a", "storage_options": [1]}, TypeError, "must be a mapping"),
        ({"path": "/a", "storage_options": {1: 2}}, TypeError, "keys must be str"),
    ],
)
def test_from_dict_invalid(data, exc, match):
    with pytest.raises(exc, match=match):
        upath_from_dict(data)


def test_serialized_upath_typeddict():
    assert SerializedUPath.__required_keys__ == frozenset({"path"})
    assert SerializedUPath.__optional_keys__ == frozenset(
        {"protocol", "storage_options"}
    )


@pytest.mark.parametrize("obj", [SerializedUPath, upath_to_dict, upath_from_dict])
def test_runtime_type_hints(obj):
    assert typing.get_type_hints(obj)
