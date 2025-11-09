# Filesystem Spec :file_folder:

[fsspec](https://filesystem-spec.readthedocs.io/) is a Python library that provides a unified, pythonic interface for working with different storage backends. It abstracts away the differences between various storage systems, allowing you to interact with local files, cloud storage, remote systems, and specialty filesystems using a consistent API.

## What is fsspec?

fsspec is both a **specification** and a **collection of implementations** for pythonic filesystems. The project defines a standard interface that filesystem implementations should follow, then provides concrete implementations for dozens of different storage backends.

The core idea is simple: whether you're working with files on your local disk, objects in an S3 bucket, blobs in Azure storage, or data over HTTP, the API to interact with them should be the same.

### Core Functionality

fsspec provides filesystem objects with methods for common operations. All filesystem implementations inherit from `fsspec.spec.AbstractFileSystem`, which defines the standard interface that all filesystems must implement:

```python
import fsspec

# Create a filesystem instance
# Returns an AbstractFileSystem subclass for the specified protocol
fs = fsspec.filesystem('s3', anon=True)

# List files
files = fs.ls('my-bucket/data/')

# Check if file exists
exists = fs.exists('my-bucket/data/file.txt')

# Get file info
info = fs.info('my-bucket/data/file.txt')

# Read file
with fs.open('my-bucket/data/file.txt', 'r') as f:
    content = f.read()

# Write file
with fs.open('my-bucket/output.txt', 'w') as f:
    f.write('Hello, World!')

# Copy files
fs.cp('my-bucket/source.txt', 'my-bucket/dest.txt')

# Delete files
fs.rm('my-bucket/file.txt')
```

### Protocols

fsspec identifies filesystem types via **protocols**. Each protocol corresponds to a specific filesystem implementation:

- `file://` - Local filesystem
- `memory://` - In-memory filesystem (temporary, non-persistent)
- `s3://` or `s3a://` - Amazon S3
- `gs://` or `gcs://` - Google Cloud Storage
- `az://` or `abfs://` - Azure Blob Storage
- `adl://` - Azure Data Lake Gen1
- `abfss://` - Azure Data Lake Gen2 (secure)
- `http://` or `https://` - HTTP(S) access
- `ftp://` - FTP
- `sftp://` or `ssh://` - SFTP over SSH
- `smb://` - Samba/Windows file shares
- `webdav://` or `webdav+http://` - WebDAV
- `hdfs://` - Hadoop Distributed File System
- `hf://` - Hugging Face Hub
- `github://` - GitHub repositories
- `zip://` - ZIP archives
- `tar://` - TAR archives
- `gzip://` - GZIP compressed files
- `cached://` - Caching layer over other filesystems

And many more. See the [fsspec documentation](https://filesystem-spec.readthedocs.io/en/latest/api.html#built-in-implementations) for the complete list.

### Storage Options

Each filesystem implementation accepts different configuration parameters called **storage options**. These control authentication, connection settings, caching behavior, and more.
They are usually provided as keyword parameters to the
specific filesystem class on instantiation.

Common storage option patterns:

```python
import fsspec

# Authentication credentials
fs = fsspec.filesystem('s3', key='...', secret='...')

# Anonymous/public access
fs = fsspec.filesystem('s3', anon=True)

# Tokens and service accounts
fs = fsspec.filesystem('gs', token='path/to/creds.json')

# Connection settings
fs = fsspec.filesystem('sftp', host='...', port=22, username='...')

# Behavioral options
fs = fsspec.filesystem('s3', use_ssl=True, default_block_size=5*2**20)
```

Refer to the [fsspec documentation](https://filesystem-spec.readthedocs.io/en/latest/api.html#built-in-implementations) for details on what each filesystem supports.

### URI-Based Access: urlpaths

fsspec supports opening files directly using URIs. Usually a
resource is clearly defined by its 'protocol', 'storage options', and 'path'. The protocol and path can usually be
combined to a urlpath string:

```python
import fsspec

# resource
protocol = "s3"
storage_options = {"anon": True}
path = "bucket/file.txt"

# Create filesystem and open path
fs = fsspec.filesystem("s3", anon=True)
with fs.open("bucket/file.txt", "r") as f:
    content = f.read()

# Or open a file via its urlpath with storage_options
with fsspec.open('s3://bucket/file.txt', 'r', anon=True) as f:
    content = f.read()
```

### Chained Filesystems

fsspec supports composing filesystems together using the `::` separator. This allows one filesystem to be used as the target
filesystem for another:

```python
import fsspec

# Access a file inside a ZIP archive on S3
with fsspec.open('zip://data.csv::s3://bucket/archive.zip', 'r', anon=True) as f:
    content = f.read()

# Read a compressed file
with fsspec.open('tar://file.txt::s3://bucket/archive.tar', 'r', anon=True) as f:
    content = f.read()
```

### Caching

fsspec includes powerful caching capabilities to improve performance when accessing remote files:

```python
import fsspec

# Simple caching
fs = fsspec.filesystem(
    's3',
    anon=True,
    use_listings_cache=True,
    listings_expiry_time=600  # Cache for 10 minutes
)

# File-level caching
cached_fs = fsspec.filesystem(
    'filecache',
    target_protocol='s3',
    target_options={'anon': True},
    cache_storage='/tmp/fsspec-cache'
)
```

## When to use fsspec directly

You typically use fsspec directly when you:

- Need filesystem-level operations (`ls`, `cp`, `rm`, `find`)
- Want to work with file-like objects without path abstractions
- Need low-level control over filesystem behavior
- Are integrating with data libraries that accept fsspec URLs
- Want to implement custom filesystem wrappers
- Want to avoid the overhead of UPath instance creation

## Learn More

For comprehensive information about fsspec:

- **Official documentation**: [fsspec.readthedocs.io](https://filesystem-spec.readthedocs.io/)
- **API reference**: [Built-in filesystem implementations](https://filesystem-spec.readthedocs.io/en/latest/api.html#built-in-implementations)
- **GitHub repository**: [fsspec/filesystem_spec](https://github.com/fsspec/filesystem_spec)
- **Usage guides**: [Examples and tutorials](https://filesystem-spec.readthedocs.io/en/latest/usage.html)

For using fsspec with a pathlib-style interface, see [upath.md](upath.md).
