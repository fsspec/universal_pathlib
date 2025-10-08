import random
import string

import pytest
from fsspec.implementations.local import LocalFileSystem
from fsspec.registry import _registry as fsspec_registry_private
from fsspec.registry import known_implementations as fsspec_known_implementations
from fsspec.registry import register_implementation as fsspec_register_implementation
from fsspec.registry import registry as fsspec_registry

from upath import UPath
from upath.registry import available_implementations
from upath.registry import get_upath_class
from upath.registry import register_implementation

IMPLEMENTATIONS = {
    "abfs",
    "abfss",
    "adl",
    "az",
    "data",
    "file",
    "gcs",
    "gs",
    "hdfs",
    "http",
    "https",
    "local",
    "memory",
    "s3",
    "s3a",
    "simplecache",
    "sftp",
    "smb",
    "ssh",
    "webdav",
    "webdav+http",
    "webdav+https",
    "github",
    "zip",
    "tar",
}


@pytest.fixture(autouse=True)
def reset_registry():
    from upath.registry import _registry

    try:
        yield
    finally:
        _registry._m.maps[0].clear()  # type: ignore


@pytest.fixture()
def fake_entrypoint():
    from importlib.metadata import EntryPoint

    from upath.registry import _registry

    ep = EntryPoint(
        name="myeps",
        value="upath.core:UPath",
        group="universal_pathlib.implementations",
    )
    old_registry = _registry._entries.copy()

    try:
        _registry._entries["myeps"] = ep
        yield
    finally:
        _registry._entries.clear()
        _registry._entries.update(old_registry)


def test_available_implementations():
    impl = available_implementations()
    assert len(impl) == len(set(impl))
    assert set(impl) == IMPLEMENTATIONS


@pytest.fixture
def fake_registered_proto():
    fake_proto = "".join(random.choices(string.ascii_lowercase, k=8))

    class FakeRandomFS(LocalFileSystem):
        protocol = fake_proto

    fsspec_register_implementation(fake_proto, FakeRandomFS)
    try:
        yield fake_proto
    finally:
        fsspec_registry_private.pop(fake_proto, None)


def test_available_implementations_with_fallback(fake_registered_proto):
    impl = available_implementations(fallback=True)
    assert fake_registered_proto in impl
    assert set(impl) == IMPLEMENTATIONS.union(
        {
            *fsspec_known_implementations,
            *fsspec_registry,
        }
    )


def test_available_implementations_with_entrypoint(fake_entrypoint):
    impl = available_implementations()
    assert set(impl) == IMPLEMENTATIONS.union({"myeps"})


def test_register_implementation():
    class MyProtoPath(UPath):
        pass

    register_implementation("myproto", MyProtoPath)

    assert get_upath_class("myproto") is MyProtoPath


def test_register_implementation_wrong_input():
    with pytest.raises(TypeError):
        register_implementation(None, UPath)  # type: ignore
    with pytest.raises(ValueError):
        register_implementation("incorrect**protocol", UPath)
    with pytest.raises(ValueError):
        register_implementation("myproto", object, clobber=True)  # type: ignore
    with pytest.raises(ValueError):
        register_implementation("file", UPath, clobber=False)
    assert set(available_implementations()) == IMPLEMENTATIONS


@pytest.mark.parametrize("protocol", IMPLEMENTATIONS)
def test_get_upath_class(protocol):
    upath_cls = get_upath_class("file")
    assert issubclass(upath_cls, UPath)


def test_get_upath_class_without_implementation(clear_registry):
    with pytest.warns(
        UserWarning, match="UPath 'mock' filesystem not explicitly implemented."
    ):
        upath_cls = get_upath_class("mock")
    assert issubclass(upath_cls, UPath)


def test_get_upath_class_without_implementation_no_fallback(clear_registry):
    assert get_upath_class("mock", fallback=False) is None


def test_get_upath_class_unknown_protocol(clear_registry):
    assert get_upath_class("doesnotexist") is None


def test_get_upath_class_from_entrypoint(fake_entrypoint):
    assert issubclass(get_upath_class("myeps"), UPath)


@pytest.mark.parametrize(
    "protocol", [pytest.param("", id="empty-str"), pytest.param(None, id="none")]
)
def test_get_upath_class_falsey_protocol(protocol):
    assert issubclass(get_upath_class(protocol), UPath)
