
# Installation :package:

Getting started with `universal-pathlib` is easy! Choose your preferred package manager below and you'll be working with cloud storage in minutes.

## Quick Install

=== "uv"

    ```bash
    uv add universal-pathlib
    ```

=== "pip"

    ```bash
    python -m pip install universal-pathlib
    ```

=== "conda"

    ```bash
    conda install -c conda-forge universal-pathlib
    ```

That's it! You now have `universal-pathlib` installed. :tada:

## Filesystem-Specific Dependencies

While `universal-pathlib` comes with `fsspec` out of the box, **some filesystems require additional packages**. Don't worry—installing them is straightforward!

For example, to work with **AWS S3**, you'll need to install `s3fs`:

```bash
pip install s3fs
# or better yet, use fsspec extras:
pip install "fsspec[s3]"
```

Here are some common filesystem extras you might need:

| Filesystem | Install Command |
|------------|----------------|
| **AWS S3** | `pip install "fsspec[s3]"` |
| **Google Cloud Storage** | `pip install "fsspec[gcs]"` |
| **Azure Blob Storage** | `pip install "fsspec[azure]"` |
| **HTTP/HTTPS** | `pip install "fsspec[http]"` |
| **GitHub** | `pip install "fsspec[github]"` |
| **SSH/SFTP** | `pip install "fsspec[ssh]"` |

## Adding to Your Project

When adding `universal-pathlib` to your project, specify the filesystem extras you need. Here's a `pyproject.toml` example for a project using **S3** and **HTTP**:

```toml
[project]
name = "myproject"
requires-python = ">=3.9"
dependencies = [
    "universal_pathlib>=0.3.9",
    "fsspec[s3,http]",  # Add the filesystems you need
]
```

!!! tip "Complete List of Filesystem Extras"

    For a complete overview of all available filesystem extras and their dependencies, check out the [fsspec pyproject.toml file][fsspec-pyproject-toml]. It includes extras for:

    - Cloud storage (S3, GCS, Azure, etc.)
    - Remote protocols (HTTP, FTP, SSH, etc.)
    - Specialized systems (HDFS, WebDAV, SMB, etc.)

    [fsspec-pyproject-toml]: https://github.com/fsspec/filesystem_spec/blob/master/pyproject.toml#L26

---

<div align="center" markdown>

**Ready to get started?** Learn about [Universal Pathlib Concepts](concepts/index.md) :rocket:

</div>
