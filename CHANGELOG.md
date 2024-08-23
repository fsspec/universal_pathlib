# universal_pathlib changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
...

## [0.2.3] - 2024-08-23
### Added
- upath: add st_birthtime as standard field (#254)
- upath: added SMBPath and tests (#219)
- ci: added typesafety checks (#212)

### Fixed
- upath: fix UPath.is_absolute on <3.12 (#256)
- upath: fix UPath.rename for absolute paths (#225)
- upath._flavour: fix path parsing due to change in urllib.parse.SplitResult behavior (#236)
- upath: fixed typing regressions (#212)
- upath: update flavour sources (#224, #237, #252)
- docs: fix link to filesystem spec optional dependencies (#232)

## [0.2.2] - 2024-03-04
### Fixed
- upath: fixed comparison with pathlib.Path on py<3.12 (#203)
- upath: imports of filesystem classes are now lazy (#200)
- upath: open() now passes fsspec options through to fsspec (#204)
- upath: fixed regression for args that implement `__fspath__` different from `__str__` (#200)
- docs: fixed entrypoint examples for UPath subclass registration (#196)

## [0.2.1] - 2024-02-18
### Added
- upath: added `UPath.joinuri()` (#189)

### Fixed
- fixed `UPath` instances not hashable (#188)
- fixed missing `packaging` dependency (#187)
- fixed pypi package classifiers

## [0.2.0] - 2024-02-13
### Added
- upath: support Python 3.12 (#152)
- upath: improved subclass customization options (#173)
- upath: support `local` uri scheme (#150)
- upath: added `GitHubPath` (#155)
- upath: added `DataPath` for data uris (#169)

### Changed
- tests: xfail tests if optional dependency is missing (#160)

### Fixed
- fixed netloc handling of `memory://netloc/a/b` style uris (#162)
- fixed broken mkdir for cloud filesystems (#177)
- fixed UPath().stat() now returns a `os.stat_result`-like object (#179)

## [0.1.4]
### Changed
- upath: require fsspec>=2022.1.0 (#148).

### Fixed
- upath.implementation.local: fixes _kwargs in local sub paths (#158).
- upath: fix iterdir trailing slash (#149).
- upath: consistent glob behaviour for "**" patterns (#143).

## [0.1.3]
### Fixed
- upath: restore compatibility with "fsspec<2022.03.0" in line with setup.cfg (#139).

## [0.1.2]
### Added
- upath.registry: provide `available_implementations()` and `register_implementation()` (#134).
- upath: add `UPath.storage_options` and `UPath.protocol` (#135).

### Fixed
- upath: fix `UPath.as_uri()` (#133).

## [0.1.1]
### Fixed
- restore `._kwargs` and `._url` on `PosixUPath` and `WindowsUPath` subclasses (#131).
- tests: fixed and refactored core tests (#130).

## [0.1.0]
### Changed
- updated past changelog entries.
- changed `UPath.__new__` behavior to return `UPath` subclasses for local paths (#125).

### Fixed
- improved azure test separation (#123).

### Added
- tests to confirm pydantic `BaseSettings` behavior (#127).

## [0.0.24] - 2023-06-19
### Added
- started a changelog to keep track of significant changes (#118).
- add support for abfss protocol (#113).
- add cpython pathlib tests (#104).
- implemented `.rename` (#96).

### Fixed
- various webdav test fixes (#103, #107, #109).
- fixed issue with `._url` parsing (#102).
- improved error messages (#96).
- fixed `.rglob()` method (#96).

### Changed
- modernized package dev tools (#105).
- updated ipynb example notebook (#96).

## [0.0.23] - 2023-03-24
### Added
- Implement `UPath.resolve` with a special redirect-following implementation for `HTTPPath` (#86).

## [0.0.22] - 2023-03-11
### Fixed
- Respect exist_ok in mkdir when creating parent directories (#83).

## [0.0.21] - 2022-09-19
### Changed
- Changed the `UPath` implementation registry to lazily import implementations (#78).
- Refactored class methods (#77).

### Fixed
- Fixed S3 paths with a `+` (#76).

## [0.0.20] - 2022-08-30
### Added
- Python 3.11 compatibility (#69).

### Fixed
- Fix `.parents` (#75).
- Fix `.with_*` methods (#73).

### Changed
- Use `NotADirectoryError` instead of custom error (#74).

## [0.0.19] - 2022-06-22
### Added
- started a changelog to keep track of significant changes

[Unreleased]: https://github.com/fsspec/universal_pathlib/compare/v0.2.3...HEAD
[0.2.3]: https://github.com/fsspec/universal_pathlib/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/fsspec/universal_pathlib/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/fsspec/universal_pathlib/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/fsspec/universal_pathlib/compare/v0.1.4...v0.2.0
[0.1.4]: https://github.com/fsspec/universal_pathlib/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/fsspec/universal_pathlib/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/fsspec/universal_pathlib/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/fsspec/universal_pathlib/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/fsspec/universal_pathlib/compare/v0.0.24...v0.1.0
[0.0.24]: https://github.com/fsspec/universal_pathlib/compare/v0.0.23...v0.0.24
[0.0.23]: https://github.com/fsspec/universal_pathlib/compare/v0.0.22...v0.0.23
[0.0.22]: https://github.com/fsspec/universal_pathlib/compare/v0.0.21...v0.0.22
[0.0.21]: https://github.com/fsspec/universal_pathlib/compare/v0.0.20...v0.0.21
[0.0.20]: https://github.com/fsspec/universal_pathlib/compare/v0.0.19...v0.0.20
[0.0.19]: https://github.com/fsspec/universal_pathlib/tree/v0.0.19
