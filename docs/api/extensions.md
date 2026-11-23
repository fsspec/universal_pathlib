# Extensions :puzzle_piece:

The extensions module provides a base class for extending UPath functionality while maintaining
compatibility with all filesystem implementations.

## ProxyUPath

::: upath.extensions.ProxyUPath
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false
        members: false
        show_bases: true

---

## Usage Example

`ProxyUPath` allows you to extend the UPath interface with additional methods while
preserving compatibility with all supported filesystem implementations. It acts as a
wrapper around any UPath instance.

### Creating a Custom Extension

```python
from upath import UPath
from upath.extensions import ProxyUPath

class MyCustomPath(ProxyUPath):
    """Custom path with additional functionality"""

    def custom_method(self) -> str:
        """Add your custom functionality here"""
        return f"Custom processing for: {self.path}"

    def enhanced_read(self) -> str:
        """Enhanced read with preprocessing"""
        content = self.read_text()
        # Add custom processing
        return content.upper()

# Use with any filesystem
s3_path = MyCustomPath("s3://bucket/file.txt")
local_path = MyCustomPath("/tmp/file.txt")
gcs_path = MyCustomPath("gs://bucket/file.txt")

# All standard UPath methods work
print(s3_path.exists())
print(local_path.parent)

# Always a subclass of your class
assert isinstance(s3_path, MyCustomPath)
assert isinstance(local_path, MyCustomPath)

# Plus your custom methods
print(s3_path.custom_method())
content = local_path.enhanced_read()
```

### Restricting Supported Protocols

If your extension only works with some filesystems, set the `supported_protocols`
class attribute. Creating an instance with any other protocol raises a `TypeError`:

```python
from upath.extensions import ProxyUPath

class CloudOnlyPath(ProxyUPath):
    supported_protocols = ("s3", "gcs", "az")

    def bucket(self) -> str:
        return self.drive

CloudOnlyPath("s3://bucket/file.txt").bucket()  # 'bucket'
CloudOnlyPath("/tmp/file.txt")  # raises TypeError
```

Alternatively, you can provide the protocols as a class keyword argument:

```python
class CloudOnlyPath(ProxyUPath, supported_protocols=("s3", "gcs", "az")):
    ...
```

A few things to keep in mind:

- `supported_protocols = None` (the default) supports all protocols.
- Protocols are considered equal if fsspec maps them to the same filesystem class.
  So `"gcs"` also allows `"gs"` paths, `"s3"` allows `"s3a"`, `"az"` allows `"abfs"`
  and `"abfss"`, and `"file"` allows `"local"` and local paths without a protocol.
- The restriction is checked against the path's `protocol`. Chained paths like
  `"simplecache::s3://bucket/file.txt"` have the `"simplecache"` protocol.
- Subclasses inherit the restriction and can override it.
- Methods returning paths on another filesystem, like `joinuri()`, `copy()` or
  `move()`, raise a `TypeError` if the target protocol is not supported. `copy()`
  and `move()` check this before any data is copied.

---

## See Also :link:

- [UPath](index.md) - Main UPath class documentation
- [Implementations](implementations.md) - Built-in UPath subclasses
- [Registry](registry.md) - Implementation registry
