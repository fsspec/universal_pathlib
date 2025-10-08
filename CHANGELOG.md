# universal_pathlib changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.3] - 2025-10-08
### Added
- upath.implementations: add `ZipPath` for ZIP archive filesystem access (#442)
- upath.implementations: add `TarPath` for TAR archive filesystem access (#443)
- tests: add chained ZIP and TAR path tests (#440)

### Fixed
- upath.core: remove `chain_parser` parameter from type overloads to improve type narrowing (#436)

### Changed
- docs: update README with notes about `__fspath__()` behavior

## [0.3.2] - 2025-10-05
### Added
- upath.types: add storage_options submodule with TypedDict classes for all filesystem implementations (#432)
- upath.implementations: add storage_options type annotations to all UPath subclass constructors (#432)
- upath: add type overloads to narrow UPath type based on protocol parameter (#431)
- upath.registry: add overloads to `get_upath_class()` to return correct subclass type based on protocol (#429)
- typesafety: add comprehensive tests for storage_options type checking (#432)
- typesafety: add tests for protocol-based type narrowing (#429, #431)

### Fixed
- upath: fix chained paths `.path` property to return correct normalized paths (#426)
- upath.implementations: correct `.path` normalization for cloud and http paths (#426)
- upath._protocol: raise error when explicitly requesting empty protocol but another protocol is found (#430)
- upath.core: adjust Pydantic v2 schema to support None protocol (#430)
- tests: add xfail when hitting GitHub rate limit (#429)

## [0.3.1] - 2025-10-03
### Added
- upath: add `UPath.from_uri()` classmethod (#423)
- upath: add `UPath.move_into()` method (#422)
- upath: implement `.info` property (#416)
- typesafety: add thorough typechecks to UPath interface (#414)

### Fixed
- upath: fix type annotations for upath.core, upath.extensions and upath.implementations (#420)
- upath: backport types and methods to local implementations (#421)
- upath: stricter upath types and remove Compat* protocol (#417)

### Changed
- maintenance: update license identifier and restrict ci permissions (#424)

## [0.3.0] - 2025-09-29
### Fixed
- upath: support relative paths (#405)
- upath: implement chain functionality (#346)
- upath: fix upath suffixes (#407)
- upath: update flavours (#350, #351, #400, #403, #411)
- upath: fix GH test skipping (#361)
- ci: update ubuntu runners (#359)
- ci: address skip_existing deprecation (#369)
- tests: split protocol mismatch test (#365)
- tests: ensure non-local upaths raise with builtin open (#368)
- tests: add an xfail test for // behaviour on s3 (#370)
- tests: fix xfail call args (#409)
- tests: add a os.PathLike test (#410)

### Added
- upath: api extensions via `upath.extensions.ProxyUPath` (#372)
- upath: add upath.types in preparation for deriving from pathlib-abc (#364)
- upath: add optional support for pydantic (#395)
- upath: list late registered protocols (#358)
- repo: add a security policy (#327)
- ci: start running against 3.14 (#363)

### Changed
- upath: inherit from `pathlib_abc.ReadablePath` and `pathlib_abc.WritablePath` (#366, #402, #404)
- upath: drop Python 3.8 (#360)
- upath: remove deprecated accessor support (#362)

## [0.2.6] - 2024-12-13
### Fixed
- upath: add support for 'abfss' protocol in WrappedFileSystemFlavour (#311)
- upath: fixed sftp join issue for non-root prefixed paths (#294)
- upath: fixed missing typing-extension dependency (#290)
- upath: updated flavour sources (#285, #299, #313, #319)
- tests: minor fixes for moto and gcs tests without internet connectivity (#312)

### Changed
- ci: switch to trusted publishing

### Added
- tests: allow configuring smb port via env var (#314)

## [0.2.5] - 2024-09-08
### Fixed
- upath.implementations.cloud: move bucket check to subclasses (#277)
- upath: enable local tests on windows and fix is_absolute (#278)
- upath: updated flavour sources (#273)

### Added
- upath: adds support for python-3.13 (#275)

## [0.2.4] - 2024-09-07
### Fixed
- upath: fix UPath.rename type signature (#258)
- upath: prevent SMBPath.rename warnings (#259)
- upath: implement UPath.samefile (#261)
- upath: fix UPath.touch(exists_ok=False) if file exists (#262)
- upath: UPath.joinpath() raise error on protocol mismatch (#264)
- tests: silence test warnings (#267)
- tests: fix http xpass test (#266)
- tests: use newer moto server (#248)
- tests: mkdir test on existing gcs bucket (#263)

### Added
- upath: add SFTPPath implementation (#265)

### Changed
- upath: move setup.cfg to pyproject.toml (#260)
- upath: UPath.lstat now returns but raises a warning (#271)
- upath: updated flavours to the newest versions (#272)

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

[Unreleased]: https://github.com/fsspec/universal_pathlib/compare/v0.3.3...HEAD
[0.3.3]: https://github.com/fsspec/universal_pathlib/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/fsspec/universal_pathlib/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/fsspec/universal_pathlib/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/fsspec/universal_pathlib/compare/v0.2.6...v0.3.0
[0.2.6]: https://github.com/fsspec/universal_pathlib/compare/v0.2.5...v0.2.6
[0.2.5]: https://github.com/fsspec/universal_pathlib/compare/v0.2.4...v0.2.5
[0.2.4]: https://github.com/fsspec/universal_pathlib/compare/v0.2.3...v0.2.4
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
