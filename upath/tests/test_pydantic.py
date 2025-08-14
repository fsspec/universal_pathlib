import json
from os.path import abspath

import pydantic
import pydantic_core
import pytest

from upath import UPath


@pytest.mark.parametrize("source", ["json", "python"])
def test_validate_from_str(source):
    input = "file:///my/path"

    ta = pydantic.TypeAdapter(UPath)
    if source == "json":
        output = ta.validate_json(json.dumps(input))
    else:  # source == "python"
        output = ta.validate_python(input)

    u = UPath(input)
    assert abspath(output.path) == abspath(u.path)
    assert output.protocol == u.protocol


@pytest.mark.parametrize("source", ["json", "python"])
def test_validate_from_dict(source):
    input = {
        "path": "/my/path",
        "protocol": "file",
        "storage_options": {"foo": "bar", "baz": 3},
    }

    ta = pydantic.TypeAdapter(UPath)
    if source == "json":
        output = ta.validate_json(json.dumps(input))
    else:  # source == "python"
        output = ta.validate_python(input)

    assert abspath(output.path) == abspath(input["path"])
    assert output.protocol == input["protocol"]
    assert output.storage_options == input["storage_options"]


def test_validate_from_instance():
    input = UPath("/my/path")

    output = pydantic.TypeAdapter(UPath).validate_python(input)

    assert output is input


@pytest.mark.parametrize("mode", ["json", "python"])
def test_dump(mode):
    input = UPath("/my/path", protocol="file", foo="bar", baz=3)

    output = pydantic.TypeAdapter(UPath).dump_python(input, mode=mode)

    assert output["path"] == input.path
    assert output["protocol"] == input.protocol
    assert output["storage_options"] == input.storage_options


def test_dump_non_serializable_python():
    input = UPath("/my/path", protocol="file", non_serializable=object())

    output = pydantic.TypeAdapter(UPath).dump_python(input, mode="python")

    assert (
        output["storage_options"]["non_serializable"]
        is input.storage_options["non_serializable"]
    )


def test_dump_non_serializable_json():
    input = UPath("/my/path", protocol="file", non_serializable=object())

    with pytest.raises(pydantic_core.PydanticSerializationError, match="unknown type"):
        pydantic.TypeAdapter(UPath).dump_python(input, mode="json")
