<style>
#upath-logo {
    height: 1.125em;
}
</style>

# UPath ![upath](../assets/logo-128x128.svg){: #upath-logo }

The `UPath` class is your default entry point for interacting with fsspec filesystems.
When instantiating UPath, a specific `UPath` subclass will be returned, dependent on the
detected or provided `protocol`. Here we document all methods and properties available on
UPath instances.

!!! info "Compatibility"
    All methods documented here work consistently across all supported Python versions,
    even if they were introduced in later Python versions. We consider it a bug if they
    don't :bug: so please report and issue if you run into inconsistencies.


```python
from upath import UPath
```

::: upath.core.UPath
    options:
        heading_level: 2
        merge_init_into_class: false
        inherited_members: true
        members:
        - __init__
        - protocol
        - storage_options
        - fs
        - path
        - parts
        - name
        - stem
        - drive
        - root
        - anchor
        - suffix
        - suffixes
        - parent
        - parents
        - joinpath
        - joinuri
        - with_name
        - with_stem
        - with_suffix
        - with_segments
        - relative_to
        - is_relative_to
        - match
        - full_match
        - as_posix
        - as_uri
        - open
        - read_text
        - read_bytes
        - write_text
        - write_bytes
        - iterdir
        - glob
        - rglob
        - walk
        - mkdir
        - rmdir
        - touch
        - unlink
        - rename
        - replace
        - copy
        - move
        - copy_into
        - move_into
        - exists
        - is_file
        - is_dir
        - is_symlink
        - is_absolute
        - stat
        - info
        - absolute
        - resolve
        - expanduser
        - cwd
        - home

---

## See Also :link:

- [Registry](registry.md) - The upath implementation registry
- [Implementations](implementations.md) - UPath subclasses
- [Extensions](extensions.md) - Extending UPath functionality
- [Types](types.md) - Type hints and protocols
