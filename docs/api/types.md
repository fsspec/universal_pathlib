# Types :label:

The types module provides type hints, protocols, and type aliases for working with UPath
and filesystem operations. This includes abstract base classes, type aliases for path-like
objects, and typed dictionaries for filesystem-specific storage options.

## pathlib-abc base classes

These abstract base classes and protocols are re-exported from [pathlib-abc](https://github.com/barneygale/pathlib-abc)
They define the core path interfaces that stdlib pathlib and UPath implementations conform to.

::: upath.types.JoinablePath
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false
        members: false
        show_bases: true

::: upath.types.ReadablePath
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false
        members: false
        show_bases: true

::: upath.types.WritablePath
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false
        members: false
        show_bases: true

::: upath.types.PathInfo
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false
        members: false
        show_bases: true

::: upath.types.PathParser
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false
        members: false
        show_bases: true

---

## UPath specific protocols

::: upath.types.UPathParser
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false
        members: false
        show_bases: true

---

## Type Aliases

Convenient type aliases for path-like objects used throughout UPath.

::: upath.types.JoinablePathLike
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false

Union of types that can be joined as path segments.

::: upath.types.ReadablePathLike
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false

Union of types that can be read from.

::: upath.types.WritablePathLike
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false

Union of types that can be written to.

::: upath.types.SupportsPathLike
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false

Union of objects that support `__fspath__()` or `__vfspath__()` protocols.

::: upath.types.StatResultType
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false
        members: false

Protocol for `os.stat_result`-like objects.

---

## Storage Options

Typed dictionaries providing type hints for filesystem-specific configuration options.
These help ensure correct parameter names and types when configuring different filesystems.

::: upath.types.storage_options
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false
        show_bases: false
        members:
        - SimpleCacheStorageOptions
        - GCSStorageOptions
        - S3StorageOptions
        - AzureStorageOptions
        - DataStorageOptions
        - FTPStorageOptions
        - GitHubStorageOptions
        - HDFSStorageOptions
        - HTTPStorageOptions
        - FileStorageOptions
        - MemoryStorageOptions
        - SFTPStorageOptions
        - SMBStorageOptions
        - WebdavStorageOptions
        - ZipStorageOptions
        - TarStorageOptions

---

## See Also :link:

- [UPath](index.md) - Main UPath class documentation
- [Implementations](implementations.md) - Built-in UPath subclasses
- [Extensions](extensions.md) - Extending UPath functionality
- [Registry](registry.md) - Implementation registry
