# Registry :file_cabinet:

The UPath registry system manages filesystem-specific path implementations. It allows you to
register custom UPath subclasses for different protocols and retrieve the appropriate
implementation for a given protocol.

## Functions

::: upath.registry.get_upath_class
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false

::: upath.registry.register_implementation
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false

::: upath.registry.available_implementations
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false

---

## Registering Implementations

Register a UPath subclass for a protocol with `register_implementation()`. Pass `clobber=True` to replace an already registered implementation, for example to customize the implementation used for `s3://` paths:

```python
from upath import UPath
from upath.implementations.cloud import S3Path
from upath.registry import register_implementation

class MyS3Path(S3Path):
    pass

register_implementation("s3", MyS3Path, clobber=True)
assert isinstance(UPath("s3://bucket/file.txt"), MyS3Path)
```

If you distribute your implementation in a Python package, you can register it via an entry point instead:

```toml
# pyproject.toml
[project.entry-points."universal_pathlib.implementations"]
myproto = "my_module.submodule:MyPath"
```

!!! warning "An fsspec filesystem is required"
    UPath implementations delegate all filesystem access to the fsspec filesystem registered for the same protocol. To support a new protocol, register an fsspec filesystem for it too. See [How do I create a custom UPath for a new filesystem?](../usage.md#how-do-i-create-a-custom-upath-for-a-new-filesystem) for an example.

---

## See Also :link:

- [UPath](index.md) - Main UPath class documentation
- [Implementations](implementations.md) - Built-in UPath subclasses
- [Extensions](extensions.md) - Extending UPath functionality
