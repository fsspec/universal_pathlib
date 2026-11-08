import json
import pathlib
import sys
import warnings
from os.path import abspath

import pydantic
import pydantic_core
import pytest
from fsspec.implementations.http import get_client
from packaging.version import Version

from upath import UPath
from upath.extensions import ProxyUPath
from upath.implementations.local import FilePath
from upath.implementations.local import PosixUPath
from upath.implementations.local import WindowsUPath
from upath.serializers import upath_to_dict

from .utils import only_on_windows
from .utils import skip_on_windows


def _import_pydantic_v1():
    with warnings.catch_warnings():
        # pydantic.v1 < 1.10.25 warns that it is incompatible with Python 3.14+
        warnings.simplefilter("ignore", UserWarning)
        try:
            import pydantic.v1 as pydantic_v1
        except ImportError:
            return None
    if sys.version_info >= (3, 14) and Version(pydantic_v1.VERSION) < Version(
        "1.10.25"
    ):
        return None
    return pydantic_v1


pydantic_v1 = _import_pydantic_v1()

requires_pydantic_v1 = pytest.mark.skipif(
    pydantic_v1 is None,
    reason="requires pydantic.v1 with support for this Python version",
)


@pytest.fixture(params=["v1", "v2"])
def pydantic_version(request):
    if request.param == "v1" and pydantic_v1 is None:
        pytest.skip("requires pydantic.v1 with support for this Python version")
    return request.param


@pytest.fixture(params=["json", "python"])
def source(request):
    return request.param


@pytest.fixture
def validate(pydantic_version, source):
    def _validate(value, cls=UPath):
        if pydantic_version == "v1":
            if source == "json":
                return pydantic_v1.parse_raw_as(cls, json.dumps(value))
            else:  # source == "python"
                return pydantic_v1.parse_obj_as(cls, value)
        else:
            ta = pydantic.TypeAdapter(cls)
            if source == "json":
                return ta.validate_json(json.dumps(value))
            else:  # source == "python"
                return ta.validate_python(value)

    return _validate


@pytest.fixture
def validation_error(pydantic_version):
    if pydantic_version == "v1":
        return pydantic_v1.ValidationError
    else:
        return pydantic.ValidationError


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
def test_validate_from_str(path, validate):
    expected = UPath(path)

    actual = validate(path)

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
def test_validate_from_dict(dct, validate):
    output = validate(dct)

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
        output = pydantic_v1.parse_obj_as(UPath, input)
    else:
        output = pydantic.TypeAdapter(UPath).validate_python(input)

    assert output is input


@pytest.mark.parametrize(
    "value",
    [
        1,
        None,
        ["memory:///my/path"],
        {"protocol": "memory"},
        {"path": 1},
        {"path": "/my/path", "unknown": 1},
        {"path": "/my/path", "storage_options": ["foo"]},
    ],
)
def test_validate_invalid(value, validate, validation_error):
    with pytest.raises(validation_error):
        validate(value)


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
    assert output == upath_to_dict(u)


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


def test_proxyupath_serialization():
    u = ProxyUPath("memory://my/path", some_option=True)

    ta = pydantic.TypeAdapter(ProxyUPath)
    dumped = ta.dump_python(u, mode="python")
    loaded = ta.validate_python(dumped)

    assert isinstance(loaded, ProxyUPath)
    assert loaded.path == u.path
    assert loaded.protocol == u.protocol
    assert loaded.storage_options == u.storage_options


def test_proxyupath_supported_protocols_validation():
    from upath.extensions import ProxyUPath

    class MyProxyPath(ProxyUPath, supported_protocols=("memory",)):
        pass

    ta = pydantic.TypeAdapter(MyProxyPath)
    assert isinstance(ta.validate_python("memory:///my/path"), MyProxyPath)

    with pytest.raises(pydantic.ValidationError, match="incompatible with"):
        ta.validate_json('"s3://bucket/path"')
    with pytest.raises(pydantic.ValidationError):
        ta.validate_python({"path": "bucket/path", "protocol": "s3"})


@pytest.mark.parametrize(
    "path,cls",
    [
        pytest.param("/my/path", PosixUPath, marks=skip_on_windows(None)),
        pytest.param("C:\\my\\path", WindowsUPath, marks=only_on_windows(None)),
        ("file:///my/path", FilePath),
    ],
)
def test_localpath_serialization(path, cls):
    u = UPath(path)
    assert type(u) is cls

    ta = pydantic.TypeAdapter(cls)
    dumped = ta.dump_python(u, mode="python")
    loaded = ta.validate_python(dumped)

    assert isinstance(loaded, cls)
    assert loaded.path == u.path
    assert loaded.protocol == u.protocol
    assert loaded.storage_options == u.storage_options


def test_json_schema():
    ta = pydantic.TypeAdapter(UPath)
    ta.json_schema()


@pytest.mark.parametrize(
    "cls",
    [
        UPath,
        pytest.param(PosixUPath, marks=skip_on_windows(None)),
        pytest.param(WindowsUPath, marks=only_on_windows(None)),
        FilePath,
        ProxyUPath,
    ],
)
def test_v2_does_not_use_v1_validators(cls):
    with warnings.catch_warnings():
        # pydantic v2 warns when it falls back to __get_validators__
        warnings.simplefilter("error")

        class Model(pydantic.BaseModel):
            path: cls

        ta = pydantic.TypeAdapter(cls)

    assert isinstance(Model(path={"path": "/my/path"}).path, cls)
    assert isinstance(ta.validate_python({"path": "/my/path"}), cls)


# === pydantic v1 specific tests ======================================


@requires_pydantic_v1
def test_v1_validate_from_pathlike():
    p = pathlib.Path("my", "path").absolute()

    output = pydantic_v1.parse_obj_as(UPath, p)

    assert output == UPath(p)


@requires_pydantic_v1
@pytest.mark.parametrize(
    "path,cls",
    [
        pytest.param("/my/path", PosixUPath, marks=skip_on_windows(None)),
        pytest.param("C:\\my\\path", WindowsUPath, marks=only_on_windows(None)),
        ("file:///my/path", FilePath),
    ],
)
def test_v1_localpath_validation(path, cls):
    u = UPath(path)
    assert type(u) is cls

    from_str = pydantic_v1.parse_obj_as(cls, path)
    from_dict = pydantic_v1.parse_obj_as(cls, upath_to_dict(u))

    for loaded in [from_str, from_dict]:
        assert isinstance(loaded, cls)
        assert loaded.path == u.path
        assert loaded.protocol == u.protocol
        assert loaded.storage_options == u.storage_options


@requires_pydantic_v1
def test_v1_proxyupath_validation():
    u = ProxyUPath("memory://my/path", some_option=True)

    loaded = pydantic_v1.parse_obj_as(ProxyUPath, upath_to_dict(u))

    assert isinstance(loaded, ProxyUPath)
    assert loaded.path == u.path
    assert loaded.protocol == u.protocol
    assert loaded.storage_options == u.storage_options


@requires_pydantic_v1
@pytest.mark.parametrize(
    ("args", "kwargs"),
    [
        (("memory:///my/path",), {}),
        (("/my/path",), {"protocol": "file", "foo": "bar", "baz": 3}),
        (("s3://bucket/key",), {"anon": True}),
        (("https://www.example.com",), {}),
    ],
)
def test_v1_json_encoders_roundtrip(args, kwargs):
    class Model(pydantic_v1.BaseModel):
        path: UPath

        class Config:
            json_encoders = {UPath: upath_to_dict}

    u = UPath(*args, **kwargs)

    model_json = Model(path=u).json()
    loaded = Model.parse_raw(model_json)

    assert json.loads(model_json) == {"path": upath_to_dict(u)}
    assert type(loaded.path) is type(u)
    assert loaded.path.path == u.path
    assert loaded.path.protocol == u.protocol
    assert loaded.path.storage_options == u.storage_options


@requires_pydantic_v1
def test_v1_json_encoders_local_path_roundtrip():
    class Model(pydantic_v1.BaseModel):
        path: UPath

        class Config:
            json_encoders = {UPath: upath_to_dict}

    u = UPath(pathlib.Path("my", "path").absolute())

    model_json = Model(path=u).json()
    loaded = Model.parse_raw(model_json)

    # local paths are pathlib.Path subclasses and only virtual subclasses
    # of UPath, so pydantic v1 encodes them with its pathlib.Path encoder
    assert json.loads(model_json) == {"path": str(u)}
    assert type(loaded.path) is type(u)
    assert loaded.path == u


@requires_pydantic_v1
def test_v1_json_non_serializable():
    class Model(pydantic_v1.BaseModel):
        path: UPath

        class Config:
            json_encoders = {UPath: upath_to_dict}

    model = Model(path=UPath("https://www.example.com", get_client=get_client))

    assert model.dict()["path"].storage_options["get_client"] is get_client
    with pytest.raises(TypeError, match="not JSON serializable"):
        model.json()
