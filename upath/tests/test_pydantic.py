import json
from os.path import abspath

import pydantic
import pydantic_core
import pytest
from fsspec.implementations.http import get_client

from upath import UPath


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
@pytest.mark.parametrize("source", ["json", "python"])
def test_validate_from_str(path, source):
    expected = UPath(path)

    ta = pydantic.TypeAdapter(UPath)
    if source == "json":
        actual = ta.validate_json(json.dumps(path))
    else:  # source == "python"
        actual = ta.validate_python(path)

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
@pytest.mark.parametrize("source", ["json", "python"])
def test_validate_from_dict(dct, source):
    ta = pydantic.TypeAdapter(UPath)
    if source == "json":
        output = ta.validate_json(json.dumps(dct))
    else:  # source == "python"
        output = ta.validate_python(dct)

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
def test_validate_from_instance(path):
    input = UPath(path)

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
def test_dump(args, kwargs, mode):
    u = UPath(*args, **kwargs)

    output = pydantic.TypeAdapter(UPath).dump_python(u, mode=mode)

    assert output["path"] == u.path
    assert output["protocol"] == u.protocol
    assert output["storage_options"] == u.storage_options


def test_dump_non_serializable_python():
    output = pydantic.TypeAdapter(UPath).dump_python(
        UPath("https://www.example.com", get_client=get_client), mode="python"
    )

    assert output["storage_options"]["get_client"] is get_client


def test_dump_non_serializable_json():
    with pytest.raises(pydantic_core.PydanticSerializationError, match="unknown type"):
        pydantic.TypeAdapter(UPath).dump_python(
            UPath("https://www.example.com", get_client=get_client), mode="json"
        )
