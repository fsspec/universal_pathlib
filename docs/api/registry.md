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

## See Also :link:

- [UPath](index.md) - Main UPath class documentation
- [Implementations](implementations.md) - Built-in UPath subclasses
- [Extensions](extensions.md) - Extending UPath functionality
