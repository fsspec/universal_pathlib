# Universal Pathlib

[![PyPI](https://img.shields.io/pypi/v/universal_pathlib.svg)](https://pypi.org/project/universal_pathlib/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/universal_pathlib)](https://pypi.org/project/universal_pathlib/)
[![PyPI - License](https://img.shields.io/pypi/l/universal_pathlib)](https://github.com/fsspec/universal_pathlib/blob/main/LICENSE)
[![Conda (channel only)](https://img.shields.io/conda/vn/conda-forge/universal_pathlib?label=conda)](https://anaconda.org/conda-forge/universal_pathlib)

[![Tests](https://github.com/fsspec/universal_pathlib/actions/workflows/tests.yml/badge.svg)](https://github.com/fsspec/universal_pathlib/actions/workflows/tests.yml)
[![GitHub issues](https://img.shields.io/github/issues/fsspec/universal_pathlib)](https://github.com/fsspec/universal_pathlib/issues)
[![Codestyle black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Changelog](https://img.shields.io/badge/changelog-Keep%20a%20Changelog-%23E05735)](./CHANGELOG.md)

Universal Pathlib is a python library that aims to extend Python's built-in [`pathlib.Path`](https://docs.python.org/3/library/pathlib.html) api to use a variety of backend filesystems using [`fsspec`](https://filesystem-spec.readthedocs.io/en/latest/intro.html)

## Installation

### Pypi

```bash
python -m pip install universal_pathlib
```

### conda

```bash
conda install -c conda-forge universal_pathlib
```

## Basic Usage

```python
>>> from upath import UPath
>>> import s3fs

>>> s3path = UPath("s3://test_bucket") / "example.txt"
>>> s3path.name
example.txt
>>> s3path.stem
example
>>> s3path.suffix
.txt
>>> s3path.exists()
True
>>> s3path.read_text()
'Hello World'
```

For more examples, see the [example notebook here](notebooks/examples.ipynb)

### Currently supported filesystems (and schemes)

- `file:` Local filessystem
- `memory:` Ephemeral filesystem in RAM
- `az:`, `adl:`, `abfs:` and `abfss:` Azure Storage (requires `adlfs` to be installed)
- `http:` and `https:` HTTP(S)-based filesystem
- `hdfs:` Hadoop distributed filesystem
- `gs:` and `gcs:` Google Cloud Storage (requires `gcsfs` to be installed)
- `s3:` and `s3a:` AWS S3 (requires `s3fs` to be installed)
- `webdav+http:` and `webdav+https:` WebDAV-based filesystem on top of HTTP(S) (requires `webdav4[fsspec]` to be installed)

Other fsspec-compatible filesystems may also work, but are not supported and tested.
Contributions for new filesystems are welcome!

## Contributing

Contributions are very welcome.
To learn more, see the [Contributor Guide](CONTRIBUTING.rst).

## License

Distributed under the terms of the [MIT license](LICENSE),
*universal_pathlib* is free and open source software.

## Issues

If you encounter any problems,
please [file an issue](https://github.com/fsspec/universal_pathlib/issues) along with a detailed description.
