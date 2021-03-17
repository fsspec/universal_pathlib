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

>>> path = UPath(file:/some/filepath.py)
>>> path.name
filepath.py
>>> path.stem
filepath
>>> path.suffix
.py
>>> path.exists()
True
```

Some backends may require other dependencies. For example to work with S3 paths, [`s3fs`](https://s3fs.readthedocs.io/en/latest/) is required.

For more examples, see the [example notebook here](notebooks/examples.ipynb)



