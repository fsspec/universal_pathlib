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

---

## See Also :link:

- [UPath](index.md) - Main UPath class documentation
- [Implementations](implementations.md) - Built-in UPath subclasses
- [Registry](registry.md) - Implementation registry
