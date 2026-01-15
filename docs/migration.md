
# Migration Guide

This guide helps you migrate to newer versions of universal-pathlib.

!!! warning

    Please open an issue if you run into issues when migrating to a newer UPath version
    and this guide is missing information.


## Migrating to v0.4.0

Version `0.4.0` changes how `UPath` determines path equality. Previously, paths with different `storage_options` were always considered unequal. Now, equality is based on **filesystem identity** (fsid), which ignores options that don't affect which filesystem is being accessed.

### Background: The Problem with storage_options Equality

In versions prior to `0.4.0`, `UPath.__eq__` compared `storage_options` directly:

```python
# Pre-0.4.0 behavior (unintuitive)
from upath import UPath

# Same S3 file, but different auth options -> NOT equal
UPath('s3://bucket/file.txt') == UPath('s3://bucket/file.txt', anon=True)  # False

# Same local file, but different behavior options -> NOT equal
UPath('/tmp/file.txt') == UPath('/tmp/file.txt', auto_mkdir=True)  # False
```

This caused subtle bugs when comparing paths that referred to the same filesystem resource. Methods like `relative_to()` and `is_relative_to()` would fail unexpectedly:

```python
# Pre-0.4.0: This raised ValueError despite referring to the same S3 bucket
p1 = UPath('s3://bucket/dir/file.txt', anon=True)
p2 = UPath('s3://bucket/dir')
p1.relative_to(p2)  # ValueError: incompatible storage_options
```

### New Behavior: Filesystem Identity (fsid)

Starting with `0.4.0`, equality is based on filesystem identity. Two UPaths are equal if they have the same protocol, path, and filesystem identity—regardless of authentication or performance options:

```python
# v0.4.0+ behavior
from upath import UPath

# Same filesystem, different options -> equal
UPath('s3://bucket/file.txt') == UPath('s3://bucket/file.txt', anon=True)  # True
UPath('/tmp/file.txt') == UPath('/tmp/file.txt', auto_mkdir=True)          # True

# Different filesystems -> not equal
UPath('s3://bucket/file.txt') != UPath('s3://bucket/file.txt',
    endpoint_url='http://localhost:9000')  # True (MinIO vs AWS)
```

**Options ignored for equality** (don't affect filesystem identity):

- Authentication: `anon`, `key`, `secret`, `token`, `profile`
- Performance: `default_block_size`, `default_cache_type`, `max_concurrency`
- Behavior: `auto_mkdir`, `default_acl`, `requester_pays`

**Options that affect equality** (change which filesystem is accessed):

- S3: Different `endpoint_url` (e.g., AWS vs MinIO vs LocalStack)
- Azure: Different `account_name`
- SFTP/SMB/FTP: Different `host` or `port`

### Impact on Path Operations

The `relative_to()` and `is_relative_to()` methods now use filesystem identity:

```python
from upath import UPath

p1 = UPath('s3://bucket/dir/file.txt', anon=True)
p2 = UPath('s3://bucket/dir')  # Different storage_options, same filesystem

# v0.4.0+: Works because both paths are on the same S3 filesystem
p1.is_relative_to(p2)  # True
p1.relative_to(p2)     # PurePosixPath('file.txt')

# Different endpoints are correctly rejected
p3 = UPath('s3://bucket/dir', endpoint_url='http://localhost:9000')
p1.is_relative_to(p3)  # False (different filesystem)
p1.relative_to(p3)     # ValueError: incompatible filesystems
```

### Migration Checklist

If your code relied on the previous behavior where different `storage_options` meant different paths:

1. **Review equality checks**: Code that expected `UPath(url, opt1=x) != UPath(url, opt1=y)` may now return `True` if they're on the same filesystem.

2. **Check set/dict usage**: Paths that were previously distinct dict keys or set members may now collide. Note that `__hash__` already ignored `storage_options`, so this is unlikely to be a new issue.

3. **Update tests**: Tests that asserted inequality based on `storage_options` differences may need updating.

### Fallback Behavior

For filesystems where UPath cannot determine identity (e.g., memory filesystem, unknown protocols), it falls back to comparing `storage_options` directly—preserving pre-0.4.0 behavior:

```python
from upath import UPath

# Memory filesystem: no fsid, falls back to storage_options comparison
UPath('memory:///file.txt', opt=1) != UPath('memory:///file.txt', opt=2)  # True
```

## Migrating to v0.3.0

Version `0.3.0` introduced a breaking change to fix a longstanding bug related to `os.PathLike` protocol compliance. This change affects how UPath instances work with standard library functions that expect local filesystem paths.

### Background: PathLike Protocol and Local Filesystem Paths

In Python, `os.PathLike` objects and `pathlib.Path` subclasses represent **local filesystem paths**. The standard library functions like `os.remove()`, `shutil.copy()`, and similar expect paths that point to the local filesystem. However, UPath implementations like `S3Path` or `MemoryPath` do not represent local filesystem paths and should not be treated as such.

Prior to `v0.3.0`, all UPath instances incorrectly implemented `os.PathLike`, which could lead to runtime errors when non-local paths were passed to functions expecting local paths. Starting with `v0.3.0`, only local UPath implementations (`PosixUPath`, `WindowsUPath`, and `FilePath`) implement `os.PathLike`.

### Migration Strategies

If your code passes UPath instances to functions expecting `os.PathLike` objects, you have several options:

**Option 1: Explicitly Request a Local Path** (Recommended)

```python
import os
from upath import UPath

# Explicitly specify the file:// protocol to get a FilePath instance
path = UPath(__file__, protocol="file")
assert isinstance(path, os.PathLike)  # True

# Now you can safely use it with os functions
os.remove(path)
```

**Option 2: Use UPath's Filesystem Operations**

```python
from upath import UPath

# Works for any UPath implementation, not just local paths
path = UPath("s3://bucket/file.txt")
path.unlink()  # UPath's native unlink method
```

**Option 3: Use Type Checking with upath.types**

For code that needs to work with different path types, use the type hints from `upath.types` to properly specify your requirements:

```python
import os
from upath import UPath
from upath.types import (
    JoinablePathLike,
    ReadablePathLike,
    WritablePathLike,
)

def read_only_local_file(path: os.PathLike) -> str:
    """Read a file on the local filesystem."""
    with open(path) as f:
        return f.read()

def write_only_local_file(path: os.PathLike, content: str) -> None:
    """Write to a file on the local filesystem."""
    with open(path, 'w') as f:
        f.write(content)

def read_any_file(path: ReadablePathLike) -> str:
    """Read a file on any filesystem."""
    return UPath(path).read_text()

def write_any_file(path: WritablePathLike, content: str) -> None:
    """Write a file on any filesystem."""
    UPath(path).write_text(content)
```

### Example: Incorrect Code That Would Fail

The following example shows code that would incorrectly work in `v0.2.x` but properly fail in `v0.3.0`:

```python
import os
from upath import UPath

# This creates a MemoryPath, which is not a local filesystem path
path = UPath("memory:///file.txt")

# In v0.2.x this would incorrectly accept the path and fail at runtime
# In v0.3.0 this correctly fails at type-check time
os.remove(path)  # TypeError: expected str, bytes or os.PathLike, not MemoryPath
```

### Working with Polars and Object Store

When using UPath with [Polars](https://pola.rs/), be aware that Polars uses Rust's [object-store](https://docs.rs/object_store/) library instead of fsspec. This requires special handling to preserve storage options.

!!! warning "Don't Rely on Implicit String Conversion"
    Avoid passing UPath instances directly to functions that implicitly cast them to strings via `os.fspath()` or `os.path.expanduser()`. This loses storage options and can lead to authentication failures.

**Problematic Pattern:**

```python
import polars as pl
from upath import UPath

# This loses storage_options when implicitly converted to string!
path = UPath('s3://bucket/file.parquet', anon=True)
df = pl.read_parquet(path)  # anon=True is lost!
```

**Recommended Approaches:**

**Option 1: Use fsspec/s3fs as the Backend** (via file handle)

```python
import polars as pl
from upath import UPath

path = UPath("s3://bucket/file.parquet", anon=True)

# Open file handle with fsspec, preserving storage_options
df = pl.scan_parquet(path.open('rb'))
```

**Option 2: Use Polars' Native Rust Backend** (with object-store options)

```python
import polars as pl
from upath import UPath

path = UPath("s3://bucket/file.parquet", key="ACCESS_KEY", secret="SECRET_KEY")

# Convert fsspec storage_options to object-store format
object_store_options = {
    "aws_access_key_id": path.storage_options.get("key"),
    "aws_secret_access_key": path.storage_options.get("secret"),
    # Add other options as needed
}

df = pl.scan_parquet(path.as_uri(), storage_options=object_store_options)
```

!!! info "Storage Options Mapping"
    Polars uses [object-store configuration keys](https://docs.rs/object_store/latest/object_store/aws/enum.AmazonS3ConfigKey.html), which differ from fsspec's naming:

    | fsspec/s3fs | object-store |
    |-------------|--------------|
    | `key` | `aws_access_key_id` |
    | `secret` | `aws_secret_access_key` |
    | `endpoint_url` | `aws_endpoint` |
    | `region_name` | `aws_region` |

See also: [pola-rs/polars#24921](https://github.com/pola-rs/polars/issues/24921)

### Extending UPath via `_protocol_dispatch=False`

If you previously used `_protocol_dispatch=False` to enable extension of the UPath API, we now recommend subclassing `upath.extensions.ProxyUPath`. See the advanced usage documentation for examples.

## Migrating to v0.2.0

### _FSSpecAccessor Subclasses with Custom Filesystem Access Methods

If you implemented a custom accessor subclass, override the corresponding `UPath` methods in your subclass directly:

```python
# OLD: v0.1.x
from upath.core import UPath, _FSSpecAccessor

class MyAccessor(_FSSpecAccessor):
    def exists(self, path, **kwargs):
        # custom logic
        pass

class MyPath(UPath):
    _default_accessor = MyAccessor


# NEW: v0.2.0+
from upath import UPath

class MyPath(UPath):
    def exists(self, *, follow_symlinks=True):
        # custom logic
        pass
```

### _FSSpecAccessor Subclasses with Custom `__init__` Method

If you implemented a custom `__init__` method for your accessor subclass to customize fsspec filesystem instantiation, use the new `_fs_factory` or `_parse_storage_options` classmethods:

```python
# OLD: v0.1.x
import fsspec
from upath.core import UPath, _FSSpecAccessor

class MyAccessor(_FSSpecAccessor):
    def __init__(self, parsed_url, **kwargs):
        # custom filesystem setup
        super().__init__(parsed_url, **kwargs)

class MyPath(UPath):
    _default_accessor = MyAccessor


# NEW: v0.2.0+
from upath import UPath

class MyPath(UPath):
    @classmethod
    def _fs_factory(cls, protocol, storage_options):
        # custom filesystem setup
        return super()._fs_factory(protocol, storage_options)
```

### Access to `._accessor`

The `_accessor` attribute and the `_FSSpecAccessor` class are deprecated. Use `UPath().fs` to access the underlying filesystem:

```python
# OLD: v0.1.x
from upath import UPath

class MyPath(UPath):
    def mkdir(self, mode=0o777, parents=False, exist_ok=False):
        self._accessor.mkdir(self.path, **kwargs)


# NEW: v0.2.0+
from upath import UPath

class MyPath(UPath):
    def mkdir(self, mode=0o777, parents=False, exist_ok=False):
        self.fs.mkdir(self.path, **kwargs)
```

### Private Attributes to Public API

Move from deprecated private attributes to public API:

| Deprecated | v0.2.0+ |
|:-----------|:--------|
| `UPath()._path` | `UPath().path` |
| `UPath()._kwargs` | `UPath().storage_options` |
| `UPath()._drv` | `UPath().drive` |
| `UPath()._root` | `UPath().root` |
| `UPath()._parts` | `UPath().parts` |

### Access to `._url`

The `._url` attribute will likely be deprecated once `UPath()` has support for URI fragments and query parameters through a public API. If you need this functionality, please open an issue.

### Custom Path Flavours

The `_URIFlavour` class was removed. The internal `FSSpecFlavour` in `upath._flavour` is experimental. If you need custom path flavour functionality, please open an issue to discuss maintainable solutions.
