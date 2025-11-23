# Implementations :file_folder:

Universal Pathlib provides specialized UPath subclasses for different filesystem protocols.
Each implementation is optimized for its respective filesystem and may provide additional
protocol-specific functionality.

## upath.implementations.cloud

::: upath.implementations.cloud.S3Path
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false
        members: []
        show_bases: true

**Protocols:** `s3://`, `s3a://`

Amazon S3 compatible object storage implementation.

::: upath.implementations.cloud.GCSPath
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false
        members: []
        show_bases: true

**Protocols:** `gs://`, `gcs://`

Google Cloud Storage implementation.

::: upath.implementations.cloud.AzurePath
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false
        members: []
        show_bases: true

**Protocols:** `abfs://`, `abfss://`, `adl://`, `az://`

Azure Blob Storage and Azure Data Lake implementation.

::: upath.implementations.cloud.HfPath
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false
        members: []
        show_bases: true

**Protocols:** `hf://`

Hugging Face Hub implementation for accessing models, datasets, and spaces.

---

## upath.implementations.local

::: upath.implementations.local.PosixUPath
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false
        members: []
        show_bases: true

POSIX-style local filesystem paths (Linux, macOS, Unix).

::: upath.implementations.local.WindowsUPath
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false
        members: []
        show_bases: true

Windows-style local filesystem paths.

::: upath.implementations.local.FilePath
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false
        members: []
        show_bases: true

**Protocols:** `file://`, `local://`

File URI implementation for local filesystem.

---

## upath.implementations.http

::: upath.implementations.http.HTTPPath
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false
        members: []
        show_bases: true

**Protocols:** `http://`, `https://`

HTTP/HTTPS read-only filesystem implementation.

---

## upath.implementations.sftp

::: upath.implementations.sftp.SFTPPath
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false
        members: []
        show_bases: true

**Protocols:** `sftp://`, `ssh://`

SFTP (SSH File Transfer Protocol) implementation.

---

## upath.implementations.smb

::: upath.implementations.smb.SMBPath
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false
        members: []
        show_bases: true

**Protocol:** `smb://`

SMB/CIFS network filesystem implementation.

---

## upath.implementations.webdav

::: upath.implementations.webdav.WebdavPath
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false
        members: []
        show_bases: true

**Protocols:** `webdav://`, `webdav+http://`, `webdav+https://`

WebDAV protocol implementation.

---

## upath.implementations.hdfs

::: upath.implementations.hdfs.HDFSPath
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false
        members: []
        show_bases: true

**Protocol:** `hdfs://`

Hadoop Distributed File System implementation.

---

## upath.implementations.github

::: upath.implementations.github.GitHubPath
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false
        members: []
        show_bases: true

**Protocol:** `github://`

GitHub repository file access implementation.

---

## upath.implementations.zip

::: upath.implementations.zip.ZipPath
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false
        members: []
        show_bases: true

**Protocol:** `zip://`

ZIP archive filesystem implementation.

---

## upath.implementations.tar

::: upath.implementations.tar.TarPath
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false
        members: []
        show_bases: true

**Protocol:** `tar://`

TAR archive filesystem implementation.

---

## upath.implementations.memory

::: upath.implementations.memory.MemoryPath
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false
        members: []
        show_bases: true

**Protocol:** `memory://`

In-memory filesystem implementation for testing and temporary storage.

---

## upath.implementations.data

::: upath.implementations.data.DataPath
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false
        members: []
        show_bases: true

**Protocol:** `data://`

Data URL scheme implementation for embedded data.

---

## upath.implementations.ftp

::: upath.implementations.ftp.FTPPath
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false
        members: []
        show_bases: true

**Protocol:** `ftp://`

FTP (File Transfer Protocol) implementation.

---

## upath.implementations.cached

::: upath.implementations.cached.SimpleCachePath
    options:
        heading_level: 3
        show_root_heading: true
        show_root_full_path: false
        members: []
        show_bases: true

**Protocol:** `simplecache://`

Local caching wrapper for remote filesystems.

---

## See Also :link:

- [UPath](index.md) - Main UPath class documentation
- [Registry](registry.md) - Implementation registry
- [Extensions](extensions.md) - Extending UPath functionality
