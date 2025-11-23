<style>
.md-content .md-typeset h1 {
  display: none;
}
#upath-logo {
    margin-top: -2em;
}
</style>

![universal pathlib logo](assets/logo-text.svg){: #upath-logo }

[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/universal_pathlib)](https://pypi.org/project/universal_pathlib/)
[![PyPI - License](https://img.shields.io/pypi/l/universal_pathlib)](https://github.com/fsspec/universal_pathlib/blob/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/universal_pathlib.svg)](https://pypi.org/project/universal_pathlib/)
[![Conda (channel only)](https://img.shields.io/conda/vn/conda-forge/universal_pathlib?label=conda)](https://anaconda.org/conda-forge/universal_pathlib)

[![Docs](https://readthedocs.org/projects/universal-pathlib/badge/?version=latest)](https://universal-pathlib.readthedocs.io/en/latest/?badge=latest)
[![Tests](https://github.com/fsspec/universal_pathlib/actions/workflows/tests.yml/badge.svg)](https://github.com/fsspec/universal_pathlib/actions/workflows/tests.yml)
[![GitHub issues](https://img.shields.io/github/issues/fsspec/universal_pathlib)](https://github.com/fsspec/universal_pathlib/issues)
[![Codestyle black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Changelog](https://img.shields.io/badge/changelog-Keep%20a%20Changelog-%23E05735)](./changelog.md)

---

**Universal Pathlib** is a Python library that extends the [`pathlib_abc.JoinablePath`][pathlib_abc], [`pathlib_abc.Readable`][pathlib_abc], and [`pathlib_abc.Writable`][pathlib_abc] API to give you a unified, Pythonic interface for working with files, whether they're on your local machine, in S3, on GitHub, or anywhere else. Built on top of [`filesystem_spec`][fsspec], it brings the convenienve of a [`pathlib.Path`][pathlib]-like interface to cloud storage, remote filesystems, and more! :sparkles:

[pathlib_abc]: https://github.com/barneygale/pathlib-abc
[pathlib]: https://docs.python.org/3/library/pathlib.html
[fsspec]: https://filesystem-spec.readthedocs.io/en/latest/intro.html

---

If you enjoy working with Python's [pathlib][pathlib] objects to operate on local file system paths,
universal pathlib provides the same interface for many supported [ filesystem_spec ][fsspec]
implementations, from cloud-native object storage like `Amazon's S3 Storage`, `Google Cloud Storage`,
`Azure Blob Storage`, to `http`, `sftp`, `memory` stores, and many more...

If you're familiar with [ filesystem_spec ][fsspec], then universal pathlib provides a convenient
way to handle the path, protocol and storage options of a object stored on a fsspec filesystem in a
single container (`upath.UPath`). And it further provides a pathlib interface to do path operations on the
fsspec urlpath.

The great part is, if you're familiar with the [pathlib.Path][pathlib] API, you can immediately
switch from working with local paths to working on remote and virtual filesystem by simply using
the `UPath` class:

=== "The Problem"

    ```python
    # Local files: use pathlib
    from pathlib import Path
    local_file = Path("data/file.txt")
    content = local_file.read_text()

    # S3 files: use boto3/s3fs
    import boto3
    s3 = boto3.client('s3')
    obj = s3.get_object(Bucket='bucket', Key='data/file.txt')
    content = obj['Body'].read().decode('utf-8')

    # Different APIs, different patterns 😫
    ```

=== "The Solution"

    ```python
    # All files: use UPath! ✨
    from upath import UPath

    local_file = UPath("data/file.txt")
    s3_file = UPath("s3://bucket/data/file.txt")

    # Same API everywhere! 🎉
    content = local_file.read_text()
    content = s3_file.read_text()
    ```

[Learn more about why you should use Universal Pathlib →](why.md){ .md-button }

---

## Quick Start :rocket:

### Installation

```bash
pip install universal-pathlib
```

!!! tip "Installing for specific filesystems"
    To use cloud storage or other remote filesystems, install the necessary fsspec extras:

    ```bash
    pip install "universal-pathlib" "fsspec[s3,gcs,azure]"
    ```

    See the [Installation Guide](install.md) for more details.

### TL;DR Examples

```python
from upath import UPath

# Works with local paths
local_path = UPath("documents/notes.txt")
local_path.write_text("Hello, World!")
print(local_path.read_text())  # "Hello, World!"

# Works with S3
s3_path = UPath("s3://my-bucket/data/processed/results.csv")
if s3_path.exists():
    data = s3_path.read_text()

# Works with HTTP
http_path = UPath("https://example.com/data/file.json")
if http_path.exists():
    content = http_path.read_bytes()

# Works with many more! 🌟
```

---

## Currently supported filesystems

- :fontawesome-solid-folder: `file:` and `local:` Local filesystem
- :fontawesome-solid-memory: `memory:` Ephemeral filesystem in RAM
- :fontawesome-brands-microsoft: `az:`, `adl:`, `abfs:` and `abfss:` Azure Storage _(requires `adlfs`)_
- :fontawesome-solid-database: `data:` RFC 2397 style data URLs _(requires `fsspec>=2023.12.2`)_
- :fontawesome-solid-network-wired: `ftp:` FTP filesystem
- :fontawesome-brands-github: `github:` GitHub repository filesystem
- :fontawesome-solid-globe: `http:` and `https:` HTTP(S)-based filesystem
- :fontawesome-solid-server: `hdfs:` Hadoop distributed filesystem
- :fontawesome-brands-google: `gs:` and `gcs:` Google Cloud Storage _(requires `gcsfs`)_
- :simple-huggingface: `hf:` Hugging Face Hub _(requires `huggingface_hub`)_
- :fontawesome-brands-aws: `s3:` and `s3a:` AWS S3 _(requires `s3fs`)_
- :fontawesome-solid-network-wired: `sftp:` and `ssh:` SFTP and SSH filesystems _(requires `paramiko`)_
- :fontawesome-solid-share-nodes: `smb:` SMB filesystems _(requires `smbprotocol`)_
- :fontawesome-solid-cloud: `webdav:`, `webdav+http:` and `webdav+https:` WebDAV _(requires `webdav4[fsspec]`)_

!!! info "Untested Filesystems"
    Other fsspec-compatible filesystems likely work through the default implementation. If you encounter issues, please [report it our issue tracker](https://github.com/fsspec/universal_pathlib/issues)! We're happy to add official support!

---

## Getting Help :question:

Need help? We're here for you!

- :fontawesome-brands-github: [GitHub Issues](https://github.com/fsspec/universal_pathlib/issues) - Report bugs or request features
- :material-book-open-variant: [Documentation](https://universal-pathlib.readthedocs.io/) - You're reading it!

!!! tip "Before Opening an Issue"
    Please check if your question has already been answered in the documentation or existing issues.

---

## License :page_with_curl:

Universal Pathlib is distributed under the [MIT license](https://github.com/fsspec/universal_pathlib/blob/main/LICENSE), making it free and open source software. Use it freely in your projects!

---

<div align="center" markdown>

**Ready to get started?**

[Install Now](install.md){ .md-button .md-button--primary }

</div>
