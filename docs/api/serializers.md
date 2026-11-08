# Serializers :package:

The serializers module converts UPath instances to and from dictionaries containing
the `path`, `protocol` and `storage_options` of a path. This is the same format that
UPath's pydantic v2 integration uses, so you can use these functions wherever there's
no automatic integration, for example in pydantic v1 models.

```python
from upath import UPath
from upath.serializers import upath_from_dict, upath_to_dict

path = UPath("memory:///data/file.txt", foo="bar")
data = upath_to_dict(path)
# {'path': '/data/file.txt', 'protocol': 'memory', 'storage_options': {'foo': 'bar'}}
assert upath_from_dict(data) == path
```

## Functions

::: upath.serializers.upath_to_dict
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false

::: upath.serializers.upath_from_dict
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false

## Types

::: upath.serializers.SerializedUPath
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false
        members: false

---

## Pydantic v1 :gear:

Pydantic v1 models (including the `pydantic.v1` module shipped with pydantic v2)
validate `UPath` fields from strings, `os.PathLike` objects, `UPath` instances and
serialized dictionaries. Pydantic v1 has no serialization hook for custom types,
so register `upath_to_dict` as a JSON encoder:

```python
from pydantic.v1 import BaseModel
from upath import UPath
from upath.serializers import upath_to_dict

class Settings(BaseModel):
    data_dir: UPath

    class Config:
        json_encoders = {UPath: upath_to_dict}

settings = Settings(data_dir="s3://bucket/data")
print(settings.json())
# {"data_dir": {"path": "bucket/data", "protocol": "s3", "storage_options": {}}}
restored = Settings.parse_raw(settings.json())
assert restored.data_dir == settings.data_dir
```

!!! note "local paths in pydantic v1"

    Pydantic v1 selects `json_encoders` by walking the class hierarchy of a value.
    Local paths (`PosixUPath` and `WindowsUPath`) subclass `pathlib.Path` and are
    only virtual subclasses of `UPath`, so pydantic v1 encodes them as plain
    strings, which validate back into the same local path. `ProxyUPath`
    subclasses need to be added to `json_encoders` explicitly.

---

## See Also :link:

- [UPath](index.md) - Main UPath class documentation
- [Extensions](extensions.md) - Extending UPath functionality
- [Types](types.md) - Type hints and protocols
