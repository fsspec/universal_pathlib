import json
from os.path import abspath

import pydantic
import pydantic.v1 as pydantic_v1
import pydantic_core
import pytest
from fsspec.implementations.http import get_client

from upath import UPath


@pytest.fixture(params=["v1", "v2"])
def pydantic_version(request):
    return request.param


@pytest.fixture(params=["json", "python"])
def source(request):
    return request.param


@pytest.fixture
def parser(pydantic_version, source):
    if pydantic_version == "v1":
        if source == "json":
            return lambda x: pydantic_v1.tools.parse_raw_as(UPath, x)
        else:
            return lambda x: pydantic_v1.tools.parse_obj_as(UPath, x)
    else:
        ta = pydantic.TypeAdapter(UPath)
        if source == "json":
            return ta.validate_json
        else:
            return ta.validate_python


@pytest.mark.parametrize(
    "path",
    [
        "/abc",
        "file:///abc",
        "memory://abc",
        "s3://bucket/key",
        "https://www.example.com",
    ],
)
def test_validate_from_str(path, source, parser):
    expected = UPath(path)

    if source == "json":
        path = json.dumps(path)

    actual = parser(path)

    assert abspath(actual.path) == abspath(expected.path)
    assert actual.protocol == expected.protocol


@pytest.mark.parametrize(
    "dct",
    [
        {
            "path": "/my/path",
            "protocol": "file",
            "storage_options": {"foo": "bar", "baz": 3},
        }
    ],
)
def test_validate_from_dict(dct, source, parser):
    if source == "json":
        data = json.dumps(dct)
    else:
        data = dct

    output = parser(data)

    assert abspath(output.path) == abspath(dct["path"])
    assert output.protocol == dct["protocol"]
    assert output.storage_options == dct["storage_options"]


@pytest.mark.parametrize(
    "path",
    [
        "/abc",
        "file:///abc",
        "memory://abc",
        "s3://bucket/key",
        "https://www.example.com",
    ],
)
def test_validate_from_instance(path, pydantic_version):
    input = UPath(path)

    if pydantic_version == "v1":
        output = pydantic_v1.tools.parse_obj_as(UPath, input)
    else:
        output = pydantic.TypeAdapter(UPath).validate_python(input)

    assert output is input


@pytest.mark.parametrize(
    ("args", "kwargs"),
    [
        (
            ("/my/path",),
            {
                "protocol": "file",
                "foo": "bar",
                "baz": 3,
            },
        )
    ],
)
@pytest.mark.parametrize("mode", ["json", "python"])
def test_dump(args, kwargs, mode, pydantic_version):
    u = UPath(*args, **kwargs)

    if pydantic_version == "v1":
        output = u.to_dict()
    else:
        output = pydantic.TypeAdapter(UPath).dump_python(u, mode=mode)

    assert output["path"] == u.path
    assert output["protocol"] == u.protocol
    assert output["storage_options"] == u.storage_options


def test_dump_non_serializable_python(pydantic_version):
    upath = UPath("https://www.example.com", get_client=get_client)

    if pydantic_version == "v1":
        output = upath.to_dict()
    else:
        output = pydantic.TypeAdapter(UPath).dump_python(upath, mode="python")

    assert output["storage_options"]["get_client"] is get_client


def test_dump_non_serializable_json(pydantic_version):
    upath = UPath("https://www.example.com", get_client=get_client)

    if pydantic_version == "v1":
        with pytest.raises(TypeError, match="not JSON serializable"):
            json.dumps(upath.to_dict())
    else:
        with pytest.raises(
            pydantic_core.PydanticSerializationError, match="unknown type"
        ):
            pydantic.TypeAdapter(UPath).dump_python(upath, mode="json")
