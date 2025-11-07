# Pathlib :snake:

[pathlib](https://docs.python.org/3/library/pathlib.html) is a Python standard library module that provides an object-oriented interface for working with filesystem paths. It's the modern, pythonic way to handle file paths and filesystem operations, replacing the older string-based `os.path` approach.

## What is pathlib?

Introduced in Python 3.4, pathlib represents filesystem paths as objects rather than strings.

### Path Objects

In pathlib, paths are instances of `Path` (or platform-specific subclasses) that represent local filesystem paths:

```python
from pathlib import Path

# Create path objects
p = Path("/home/user/documents")
p = Path("relative/path/to/file.txt")
p = Path.home()  # User's home directory
p = Path.cwd()   # Current working directory
```

### Pure vs. Concrete Paths

pathlib distinguishes between two types of paths:

**Pure Paths** (`PurePath`, `PurePosixPath`, `PureWindowsPath`):
- Only manipulate path strings
- Don't access the filesystem
- Work on any platform regardless of OS
- Useful for path manipulation without I/O

```python
from pathlib import PurePath, PurePosixPath, PureWindowsPath

# Pure path - string manipulation only
pure = PurePath("/home/user/file.txt")
parent = pure.parent  # Works
name = pure.name      # Works
# exists = pure.exists()  # AttributeError - no filesystem access

# Platform-specific pure paths
posix = PurePosixPath("/home/user/file.txt")     # Always uses /
windows = PureWindowsPath("C:\\Users\\file.txt")  # Always uses \
```

**Concrete Paths** (`Path`, `PosixPath`, `WindowsPath`):
- Inherit from pure paths
- Actually access the filesystem
- Support operations like `.exists()`, `.stat()`, `.read_text()`
- Platform-specific: `PosixPath` on Unix, `WindowsPath` on Windows

```python
from pathlib import Path

# Concrete path - filesystem operations
p = Path("/home/user/file.txt")
exists = p.exists()           # Checks filesystem
content = p.read_text()       # Reads file
size = p.stat().st_size       # Gets file size
```

## When to use pathlib

Use pathlib when you:

- Work with local filesystem paths in Python
- Need cross-platform path handling
- Want object-oriented path manipulation

## What is pathlib-abc?

[pathlib-abc](https://github.com/barneygale/pathlib-abc) is a Python library that defines abstract base classes (ABCs) for path-like objects. It provides a formal specification for the pathlib interface that can be implemented by different path types, not just local filesystem paths.

### Abstract Base Classes for Paths

pathlib-abc extracts the core concepts from Python's pathlib module into abstract base classes. This allows library authors and framework developers to:

1. **Define path-like interfaces** that work across different storage backends
2. **Type hint** functions that accept any path-like object
3. **Implement custom path classes** that follow pathlib conventions
4. **Ensure compatibility** between different path implementations

!!! info "Relationship to Python's pathlib"
    Currently (as of Python 3.14), the standard library `pathlib.Path` does **not** inherit from public pathlib-abc classes. However, there is ongoing work to incorporate these ABCs into future Python releases.

The library defines three main abstract base classes that represent different levels of path functionality:

### JoinablePath

`JoinablePath` is the most basic path abstraction. It represents paths that can be constructed, manipulated, and joined together, but cannot necessarily access any actual filesystem.

**Key capabilities:**

- Path construction and manipulation
- String operations on paths
- Path component access (name, stem, suffix, parent, etc.)
- Path joining with the `/` operator
- Pattern matching

Think of `JoinablePath` as equivalent to pathlib's `PurePath` - it only manipulates path strings.

### ReadablePath

`ReadablePath` extends `JoinablePath` to add read-only filesystem operations. It represents paths where you can read data but not modify the filesystem.

**Adds capabilities for:**

- Reading file contents (`.read_text()`, `.read_bytes()`)
- Opening files for reading
- Checking file existence and type (`.exists()`, `.is_file()`, `.is_dir()`)
- Listing directory contents (`.iterdir()`)
- Globbing and pattern matching (`.glob()`, `.rglob()`)
- Walking directory trees (`.walk()`)
- Reading symlinks (`.readlink()`)
- Accessing file metadata (`.info` property)

### WritablePath

`WritablePath` extends `JoinablePath` (not `ReadablePath`) to add write operations. It represents paths where you can create, modify, and delete filesystem objects.

**Adds capabilities for:**

- Writing file contents (`.write_text()`, `.write_bytes()`)
- Opening files for writing
- Creating directories (`.mkdir()`)
- Creating symlinks (`.symlink_to()`)

!!! note "WritablePath Does Not Inherit from ReadablePath"
    `WritablePath` does NOT inherit from `ReadablePath`. A path that is writable is not automatically readable. In practice, most filesystem paths are both readable and writable (like `UPath` which inherits from both), but the separation allows for specialized use cases like write-only destinations or read-only sources.

## Learn More

For comprehensive information about pathlib:

- **Official documentation**: [Python pathlib documentation](https://docs.python.org/3/library/pathlib.html)
- **PEP 428**: [The pathlib module – object-oriented filesystem paths](https://www.python.org/dev/peps/pep-0428/)
- **Comparison with os.path**: [Correspondence to tools in the os module](https://docs.python.org/3/library/pathlib.html#correspondence-to-tools-in-the-os-module)

For comprehensive information about pathlib-abc:

- **GitHub repository**: [barneygale/pathlib-abc](https://github.com/barneygale/pathlib-abc)

For using pathlib-style paths with remote and cloud filesystems, see [upath.md](upath.md).
