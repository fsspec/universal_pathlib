<style>
#upath-logo {
    height: 1.125em;
}
</style>

# Universal Pathlib ![upath](../assets/logo-128x128.svg){: #upath-logo }

**universal-pathlib** (imported as `upath`) bridges Python's [pathlib](https://docs.python.org/3/library/pathlib.html) API with [fsspec](https://filesystem-spec.readthedocs.io/)'s filesystem implementations. It provides a familiar, pathlib-style interface for working with files across local storage, cloud services, and remote systems.

## The Best of Both Worlds

universal-pathlib combines:

- **fsspec's filesystem support**: Access to S3, GCS, Azure, HDFS, HTTP, SFTP, and dozens more backends
- **pathlib's elegant API**: Object-oriented paths, `/` operator, `.exists()`, `.read_text()`, etc.

This means you can write code using the pathlib syntax you already know, and it works seamlessly across any storage system that fsspec supports.

## How UPath and Path Relate via pathlib-abc

`UPath` and `pathlib.Path` are related through the abstract base classes defined in [pathlib-abc](https://github.com/barneygale/pathlib-abc). While they share a common API design, they serve different purposes and have distinct inheritance hierarchies.

### The Class Hierarchy

The following diagram shows how `UPath` implementations relate to `pathlib` classes through the `pathlib_abc` abstract base classes:

```mermaid
flowchart TB

  subgraph p0[pathlib_abc]
    X ----> Y
    X ----> Z
  end

  subgraph s0[pathlib]
    X -.-> A

    A----> B
    A--> AP
    A--> AW

    Y -.-> B
    Z -.-> B

    B--> BP
    AP----> BP
    B--> BW
    AW----> BW
  end
  subgraph s1[upath]
    Y ---> U
    Z ---> U

    U --> UP
    U --> UW
    BP ---> UP
    BW ---> UW
    U --> UL
    U --> US3
    U --> UH
    U -.-> UO
  end

  X(JoinablePath)
  Y(WritablePath)
  Z(ReadablePath)

  A(PurePath)
  AP(PurePosixPath)
  AW(PureWindowsPath)
  B(Path)
  BP(PosixPath)
  BW(WindowsPath)

  U(UPath)
  UP(PosixUPath)
  UW(WindowsUPath)
  UL(FilePath)
  US3(S3Path)
  UH(HttpPath)
  UO(...Path)

  classDef na fill:#f7f7f7,stroke:#02a822,stroke-width:2px,color:#333
  classDef np fill:#f7f7f7,stroke:#2166ac,stroke-width:2px,color:#333
  classDef nu fill:#f7f7f7,stroke:#b2182b,stroke-width:2px,color:#333

  class X,Y,Z na
  class A,AP,AW,B,BP,BW,UP,UW np
  class U,UL,US3,UH,UO nu

  style UO stroke-dasharray: 3 3

  style p0 fill:none,stroke:#0a2,stroke-width:3px,stroke-dasharray:3,color:#0a2
  style s0 fill:none,stroke:#07b,stroke-width:3px,stroke-dasharray:3,color:#07b
  style s1 fill:none,stroke:#d02,stroke-width:3px,stroke-dasharray:3,color:#d02
```

**Legend:**

- **Green (pathlib_abc)**: Abstract base classes defining the path interface
- **Blue (pathlib)**: Standard library path classes for local filesystems
- **Red (upath)**: Universal pathlib classes for all filesystems
- Solid lines: Direct inheritance
- Dotted lines: Conceptual relationship (not actual inheritance yet)

### Understanding the Relationships

**pathlib-abc Layer (Green):**

- `JoinablePath` - Basic path manipulation without filesystem access
- `ReadablePath` - Adds read-only filesystem operations
- `WritablePath` - Adds write filesystem operations

**pathlib Layer (Blue):**

- `PurePath` - Pure path manipulation (similar to `JoinablePath` conceptually)
- `Path` - Concrete local filesystem paths (conceptually similar to `ReadablePath` + `WritablePath`)
- Platform-specific: `PosixPath`, `WindowsPath`, etc.

**universal-pathlib Layer (Red):**

- `UPath` - Universal path for any filesystem backend
- Local implementations: `PosixUPath`, `WindowsUPath`, `FilePath`
- Remote implementations: `S3Path`, `HttpPath`, and others

### Key Differences

**Current State (Python 3.9-3.13):**

```python
from pathlib import Path
from upath import UPath
from upath.types import JoinablePath, ReadablePath, WritablePath

# UPath explicitly implements pathlib-abc
path = UPath("s3://bucket/file.txt")
assert isinstance(path, JoinablePath)  # True
assert isinstance(path, ReadablePath)   # True
assert isinstance(path, WritablePath)   # True

# pathlib.Path does NOT (yet) inherit from pathlib-abc
local = Path("/home/user/file.txt")
assert isinstance(local, JoinablePath)  # False
assert isinstance(local, ReadablePath)   # False
assert isinstance(local, WritablePath)   # False
```

**Important Note:** The dotted lines in the diagram represent a conceptual relationship. While `pathlib.Path` doesn't currently inherit from `pathlib_abc` classes, it implements a compatible API. Future Python versions may formalize this relationship.

### Local Path Compatibility

For local filesystem paths, `UPath` provides implementations that are 100% compatible with stdlib `pathlib`:

```python
from pathlib import Path, PosixPath, WindowsPath
from upath import UPath

# Without protocol -> returns platform-specific UPath
local = UPath("/home/user/file.txt")
assert isinstance(local, UPath)           # True
assert isinstance(local, PosixPath)       # True (on Unix systems)
assert isinstance(local, Path)            # True

# With file:// protocol -> returns FilePath (fsspec-based)
file_path = UPath("file:///home/user/file.txt")
assert isinstance(file_path, UPath)       # True
assert not isinstance(file_path, Path)    # False (uses fsspec instead)
```

**PosixUPath and WindowsUPath:**
- Subclass both `UPath` and `pathlib.Path`
- 100% compatible with stdlib pathlib for local paths
- Tested against CPython's pathlib test suite
- Implement `os.PathLike` protocol

**FilePath:**
- Subclass of `UPath` only
- Uses fsspec's `LocalFileSystem` for file access
- Useful for consistent fsspec-based access across all backends
- Implements `os.PathLike` protocol

### Remote and Cloud Paths

For remote filesystems, `UPath` implementations provide the pathlib API backed by fsspec:

```python
from upath import UPath

# S3Path
s3 = UPath("s3://bucket/file.txt")
assert isinstance(s3, UPath)
assert not isinstance(s3, Path)  # Not a local path

# HttpPath
http = UPath("https://example.com/data.json")
assert isinstance(http, UPath)
assert not isinstance(http, Path)  # Not a local path
```

### Why This Design?

This architecture provides several benefits:

1. **Unified API**: Same pathlib interface works across all backends
2. **Type Safety**: pathlib-abc provides formal type hints for path operations
3. **Local Compatibility**: `PosixUPath`/`WindowsUPath` maintain full stdlib compatibility
4. **Flexibility**: Easy to add new filesystem implementations
5. **Future-Proof**: Ready for potential stdlib integration of pathlib-abc

### Writing Filesystem-Agnostic Code

Use pathlib-abc types to write code that works with both `Path` and `UPath`:

```python
from upath.types import ReadablePath, WritablePath

def process_file(input_path: ReadablePath, output_path: WritablePath) -> None:
    """Works with Path, UPath, or any ReadablePath/WritablePath implementation."""
    data = input_path.read_text()
    processed = data.upper()
    output_path.write_text(processed)

# Works with stdlib Path
from pathlib import Path
process_file(Path("input.txt"), Path("output.txt"))

# Works with UPath for cloud storage
from upath import UPath
process_file(
    UPath("s3://input-bucket/data.txt", anon=True),
    UPath("s3://output-bucket/result.txt")
)

# Mix local and remote
process_file(
    UPath("https://example.com/data.txt"),
    Path("/tmp/result.txt")
)
```

## Path Equality and Filesystem Identity

Unlike `pathlib.Path` which compares paths by their string representation alone, `UPath` considers **filesystem identity** when comparing paths. Two UPaths are equal if they refer to the same file on the same filesystem.

### How Equality Works

```python
from upath import UPath

# Same path, same filesystem -> equal (even with different options)
UPath('s3://bucket/file.txt') == UPath('s3://bucket/file.txt', anon=True)  # True

# Same path, different filesystem -> not equal
UPath('s3://bucket/file.txt') != UPath('s3://bucket/file.txt',
    endpoint_url='http://localhost:9000')  # True
```

### Filesystem Identity (fsid)

UPath uses **fsid** (filesystem identifier) to determine if two paths are on the same filesystem. If a cached filesystem exists and implements fsid, that value is used. Otherwise, fsid is computed from the protocol, storage_options, and fsspec global config (`fsspec.config.conf`), **without instantiating the filesystem**. This allows path comparison to work abstractly without requiring credentials or network access.

Unlike fsspec filesystems which raise `NotImplementedError` when fsid is not implemented, `UPath.fsid` returns `None` if the filesystem identity cannot be determined (e.g., for unknown protocols or wrapper filesystems). When fsid is `None`, path comparison falls back to comparing `storage_options` directly:

| Filesystem | Identity Based On |
|------------|-------------------|
| Local (`file://`, paths) | Always `"local"` |
| HTTP/HTTPS | Always `"http"` |
| S3 | `endpoint_url` (AWS endpoints normalized) |
| GCS | Always `"gcs"` (single global endpoint) |
| Azure Blob | `account_name` |
| SFTP/SSH | `host` + `port` |
| SMB | `host` + `port` |

Options like authentication (`anon`, `key`, `token`), performance settings (`block_size`), and behavior flags (`auto_mkdir`) don't affect filesystem identity.

### Impact on Path Operations

Filesystem identity affects `relative_to()`, `is_relative_to()`, and parent comparisons:

```python
from upath import UPath

base = UPath('s3://bucket/data')
child = UPath('s3://bucket/data/file.txt', anon=True)

# Works: same filesystem despite different storage_options
child.relative_to(base)     # PurePosixPath('file.txt')
child.is_relative_to(base)  # True
base in child.parents       # True
```

### Comparison with pathlib.Path

| Aspect | `pathlib.Path` | `UPath` |
|--------|----------------|---------|
| Equality based on | Path string only | Protocol + path + filesystem identity |
| `storage_options` | N/A | Ignored if fsid can be determined |
| Different credentials | N/A | Equal (same filesystem) |
| Different endpoints | N/A | Not equal (different filesystem) |

## Learn More

- **pathlib concepts**: See [pathlib.md](pathlib.md) for details on the pathlib API
- **fsspec backends**: See [filesystems.md](fsspec.md) for information about available filesystems
- **API reference**: Check the [API documentation](../api/index.md) for complete method details
- **fsspec details**: Visit [fsspec documentation](https://filesystem-spec.readthedocs.io/) for filesystem-specific options
- **Migration guide**: See [migration.md](../migration.md) for version-specific changes
