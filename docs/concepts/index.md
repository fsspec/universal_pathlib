# Overview :map:

Universal Pathlib brings together fsspec and pathlib to provide a unified, pythonic interface for working with files across different storage systems. Understanding how these components work together will help you make the most of universal-pathlib.

- **[Filesystem Spec](fsspec.md)** provides the foundation—a specification and collection of filesystem implementations that offer consistent access to local storage, cloud services, and remote systems.
- **[Pathlib](pathlib.md)** defines the familiar object-oriented API from Python's standard library for working with filesystem paths.
- **[Universal Pathlib](upath.md)** ties them together, implementing the [pathlib-abc](https://github.com/barneygale/pathlib-abc) interface on top of fsspec filesystems to give you a Path-like experience everywhere.

Start with [fsspec filesystems](fsspec.md) to understand the available storage backends, then explore [stdlib pathlib](pathlib.md) to learn about the path interface, and finally see [upath](upath.md) to discover how universal-pathlib combines them into a powerful, unified API.
