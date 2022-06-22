# Universal Pathlib

Universal Pathlib is a python library that aims to extend Python's built-in [`pathlib.Path`](https://docs.python.org/3/library/pathlib.html) api to use a variety of backend filesystems using [`fsspec`](https://filesystem-spec.readthedocs.io/en/latest/intro.html)

## Installation

### Pypi

```bash
pip install universal_pathlib
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
- `az:`, `adl:` and `abfs:` Azure Storage (requires `adlfs` to be installed)
- `http:` and `https:` HTTP(S)-based filesystem
- `hdfs:` Hadoop distributed filesystem
- `gs:` and `gcs:` Google Cloud Storage (requires `gcsfs` to be installed)
- `s3:` and `s3a:` AWS S3 (requires `s3fs` to be installed)
- `webdav+http:` and `webdav+https:` WebDAV-based filesystem on top of HTTP(S) (requires `webdav4[fsspec]` to be installed)

Other fsspec-compatible filesystems may also work, but are not supported and tested.
Contributions for new filesystems are welcome!

## License

MIT License
