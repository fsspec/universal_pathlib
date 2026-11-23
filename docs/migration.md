
# Migration Guide

This guide helps you migrate to newer versions of universal-pathlib.

!!! warning

    Please open an issue if you run into issues when migrating to a newer UPath version
    and this guide is missing information.


## Migrating to v0.3.0

Version `0.3.0` introduced a breaking change to fix a longstanding bug related to `os.PathLike` protocol compliance. This change affects how UPath instances work with standard library functions that expect local filesystem paths.

### Background: PathLike Protocol and Local Filesystem Paths

In Python, `os.PathLike` objects and `pathlib.Path` subclasses represent **local filesystem paths**. The standard library functions like `os.remove()`, `shutil.copy()`, and similar expect paths that point to the local filesystem. However, UPath implementations like `S3Path` or `MemoryPath` do not represent local filesystem paths and should not be treated as such.

Prior to `v0.3.0`, all UPath instances incorrectly implemented `os.PathLike`, which could lead to runtime errors when non-local paths were passed to functions expecting local paths. Starting with `v0.3.0`, only local UPath implementations (`PosixUPath`, `WindowsUPath`, and `FilePath`) implement `os.PathLike`.

**Why was `__fspath__` removed from non-local paths?**

- `os.fspath()` promises a path on the *local* filesystem. Functions like `open()`, `os.stat()` or `shutil.copy()` use the returned string to access local files, and can't do anything sensible with `"s3://bucket/file.txt"`.
- The string returned by the old `__fspath__` only contained the protocol and the path. The `storage_options` of the UPath (credentials, endpoints, account names, ...) can't be represented in that string. Libraries that converted a UPath via `os.fspath()` and then opened the URI with their own I/O layer (for example pandas, pyarrow, or polars) silently dropped these options, which caused authentication errors or requests to the wrong endpoint.
- `UPath` is built on the `pathlib_abc` base classes `JoinablePath`, `ReadablePath` and `WritablePath`. Following the standard library model, only paths that point to the local filesystem implement `os.PathLike`.

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

### Code That Checks `isinstance(path, pathlib.Path)`

Remote UPath implementations like `S3Path` are no longer subclasses of `pathlib.Path`. Only the implementations returned for local paths **without** a protocol are:

| Example | Returned class | `pathlib.Path` subclass | `os.PathLike` |
|:--------|:---------------|:-----------------------:|:-------------:|
| `UPath("/tmp/file.txt")` | `PosixUPath` / `WindowsUPath` | ✅ | ✅ |
| `UPath("file:///tmp/file.txt")` | `FilePath` | ❌ | ✅ |
| `UPath("memory:///file.txt")` | `MemoryPath` | ❌ | ❌ |
| `UPath("s3://bucket/file.txt")` | `S3Path` | ❌ | ❌ |

`PosixUPath` and `WindowsUPath` subclass `pathlib.PosixPath` and `pathlib.WindowsPath`, and they will stay `pathlib.Path` subclasses for the foreseeable future. `FilePath` and all remote implementations are not `pathlib.Path` subclasses.

An `isinstance(path, pathlib.Path)` check usually tries to answer one of two questions. Replace it with a check that answers the question you actually have:

```python
import os
import pathlib

from upath import UPath


def as_upath(path) -> UPath:
    """Use the pathlib API for local and remote paths."""
    if isinstance(path, UPath):
        return path
    # upcasts str and pathlib.Path; local paths become PosixUPath/WindowsUPath
    return UPath(path)


def is_local(path) -> bool:
    """Can the path be passed to open(), os.stat(), shutil.copy(), ...?"""
    return isinstance(path, os.PathLike)


p = as_upath(pathlib.Path("/tmp/file.txt"))
assert isinstance(p, UPath) and isinstance(p, pathlib.Path)
assert is_local(p)
assert is_local(UPath("file:///tmp/file.txt"))
assert not is_local(UPath("s3://bucket/file.txt"))
```

Upcasting `pathlib.Path` instances to `UPath` has little downside: `PosixUPath` and `WindowsUPath` behave like their `pathlib` base classes, and additionally backport newer `pathlib` features to older Python versions.

### Using UPath with pandas, pyarrow and polars

Before `v0.3.0` many data libraries accepted UPath instances, because they converted them to a string via `os.fspath()`. Now, passing a non-local UPath directly to them fails, for example with:

- pandas: `ValueError: Invalid file path or buffer object type: <class 'upath.implementations.cloud.S3Path'>`
- pyarrow: `TypeError: cannot construct a FileSource from s3://bucket/file.parquet`
- polars: `TypeError: Object does not have a .read() method.`

Even when it worked, the conversion silently dropped all storage options. Instead, pass the information these libraries need explicitly. The examples below use this path:

```python
from upath import UPath

path = UPath(
    "s3://bucket/data/file.parquet",
    key="ACCESS_KEY",
    secret="SECRET_KEY",
    endpoint_url="https://s3.example.com",
)
```

!!! warning "`str(path)` and `path.as_uri()` drop the storage options"
    Both return only the protocol and the path, i.e. `"s3://bucket/data/file.parquet"`. Credentials, endpoints and all other `storage_options` are not part of the string, so you have to pass them on separately. Also note that `as_uri()` raises a `ValueError` for relative UPaths (for example the result of `relative_to()`).

#### pandas

pandas uses fsspec to access URLs and accepts fsspec storage options via its `storage_options` argument:

```python
import pandas as pd

df = pd.read_parquet(path.as_uri(), storage_options=dict(path.storage_options))
df.to_parquet(path.as_uri(), storage_options=dict(path.storage_options))
```

The same works for `read_csv()`, `to_excel()` and all other pandas I/O functions with a `storage_options` argument. Alternatively, open the file via UPath and pass the file object:

```python
with path.open("rb") as f:
    df = pd.read_parquet(f)
```

#### pyarrow

pyarrow accepts fsspec filesystem instances via its `filesystem` argument and wraps them automatically. Pass the filesystem `path.fs` together with `path.path`, the path without the protocol:

```python
import pyarrow.dataset as ds
import pyarrow.parquet as pq

table = pq.read_table(path.path, filesystem=path.fs)
pq.write_table(table, path.path, filesystem=path.fs)

dataset = ds.dataset(path.parent.path, filesystem=path.fs, format="parquet")
```

This also works for pandas with the pyarrow engine: `pd.read_parquet(path.path, filesystem=path.fs)`.

#### polars

Polars doesn't use fsspec for cloud storage, but Rust's [object-store](https://docs.rs/object_store/) library. You have two options.

**Option 1: Use fsspec for I/O** by passing a file object. This works for every filesystem supported by UPath, but might be slower than polars' native readers:

```python
import polars as pl

with path.open("rb") as f:
    df = pl.read_parquet(f)

with path.with_name("output.parquet").open("wb") as f:
    df.write_parquet(f)
```

**Option 2: Use polars' native object-store backend** by passing the URI and translating the fsspec storage options to object-store configuration keys:

```python
import polars as pl


def s3_object_store_options(path: UPath) -> dict:
    """Translate common s3fs storage options to object-store config keys."""
    so = path.storage_options
    keys = {
        "key": "aws_access_key_id",
        "secret": "aws_secret_access_key",
        "token": "aws_session_token",
        "endpoint_url": "aws_endpoint",
    }
    options = {new: so[old] for old, new in keys.items() if old in so}
    if "region_name" in so.get("client_kwargs", {}):
        options["aws_region"] = so["client_kwargs"]["region_name"]
    if so.get("anon"):
        options["aws_skip_signature"] = "true"
    return options


df = pl.read_parquet(path.as_uri(), storage_options=s3_object_store_options(path))
lf = pl.scan_parquet(path.as_uri(), storage_options=s3_object_store_options(path))
```

!!! info "Storage Options Mapping"
    Polars uses [object-store configuration keys](https://docs.rs/object_store/latest/object_store/aws/enum.AmazonS3ConfigKey.html), which differ from fsspec's naming. For S3 the most common ones are:

    | fsspec/s3fs | object-store |
    |-------------|--------------|
    | `key` | `aws_access_key_id` |
    | `secret` | `aws_secret_access_key` |
    | `token` | `aws_session_token` |
    | `endpoint_url` | `aws_endpoint` |
    | `client_kwargs={"region_name": ...}` | `aws_region` |
    | `anon=True` | `aws_skip_signature="true"` |

    For Google Cloud Storage and Azure, see object-store's [GoogleConfigKey](https://docs.rs/object_store/latest/object_store/gcp/enum.GoogleConfigKey.html) and [AzureConfigKey](https://docs.rs/object_store/latest/object_store/azure/enum.AzureConfigKey.html). A helper method to convert storage options to the object-store format is planned (see [#459](https://github.com/fsspec/universal_pathlib/issues/459)).

See also: [pola-rs/polars#24921](https://github.com/pola-rs/polars/issues/24921)

### Extending UPath via `_protocol_dispatch=False`

Setting `_protocol_dispatch = False` on a UPath subclass was a workaround to make `MyPath(...)` return instances of `MyPath` for all protocols. It's deprecated, emits a `DeprecationWarning`, and will be removed in a future version. Because it bypasses the protocol specific UPath implementations, it can lead to incorrect behavior, for example for relative local paths.

Subclass `upath.extensions.ProxyUPath` instead. It wraps the correct UPath implementation for every protocol and returns instances of your class from all path operations:

```python
# OLD (deprecated)
from upath import UPath

class MyPath(UPath):
    _protocol_dispatch = False

    def hello(self) -> str:
        return f"Hello {self.name}!"


# NEW
from upath.extensions import ProxyUPath

class MyPath(ProxyUPath):

    def hello(self) -> str:
        return f"Hello {self.name}!"


p = MyPath("relative/file.txt")
assert str(p) == "relative/file.txt"
assert isinstance(p.parent, MyPath)
assert MyPath("s3://bucket/file.txt").hello() == "Hello file.txt!"
```

See [How do I add custom methods to UPath?](usage.md#how-do-i-add-custom-methods-to-upath) and the [ProxyUPath API reference](api/extensions.md) for more examples.

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
