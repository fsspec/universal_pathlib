# Why Use Universal Pathlib? :sparkles:

If you've ever worked with cloud storage or remote filesystems in Python, you've probably experienced the frustration of juggling different APIs. Universal Pathlib solves this problem elegantly by bringing the beloved `pathlib.Path` interface to *any* filesystem spec filesystem.

---

## The Problem: Filesystem dependent APIs :broken_heart:

Let's face it: working with files across different storage backends is messy.

### Example: The Old Way

```python
# Local files
from pathlib import Path
local_file = Path("data/results.csv")
with local_file.open('r') as f:
    data = f.read()

# S3 files
import boto3
s3 = boto3.resource('s3')
obj = s3.Object('my-bucket', 'data/results.csv')
data = obj.get()['Body'].read().decode('utf-8')

# Azure Blob Storage
from azure.storage.blob import BlobServiceClient
blob_client = BlobServiceClient.from_connection_string(conn_str)
container_client = blob_client.get_container_client('my-container')
blob_client = container_client.get_blob_client('data/results.csv')
data = blob_client.download_blob().readall().decode('utf-8')

# Three different APIs, three different patterns 😫
```

Each storage backend has its own:

- :material-api: **Different API** - Learn a new interface for each service
- :material-puzzle: **Different patterns** - Different ways to read, write, and list files
- :material-code-braces: **Different imports** - Manage multiple dependencies
- :material-hammer-wrench: **Different configurations** - Each with unique setup requirements

!!! danger "The Maintenance Nightmare"
    Want to switch from S3 to GCS? Rewrite your code. Need to support multiple backends? Write wrapper functions. Testing? Mock each service differently. This doesn't scale!

---

## The Solution: One API to Rule Them All :crown:

Universal Pathlib provides a single, unified interface that works everywhere:

```python
from upath import UPath

# Local files
local_file = UPath("data/results.csv")

# S3 files
s3_file = UPath("s3://my-bucket/data/results.csv")

# Azure Blob Storage
azure_file = UPath("az://my-container/data/results.csv")

# Same API everywhere! ✨
for path in [local_file, s3_file, azure_file]:
    with path.open('r') as f:
        data = f.read()
```

!!! success "One API, Infinite Possibilities"
    Write your code once, run it anywhere. Switch backends by changing a URL. Test locally, deploy to the cloud. It just works! :sparkles:

---

## Key Benefits :trophy:

### 1. Familiar and Pythonic :snake:

If you know Python's `pathlib`, you already know Universal Pathlib!

```python
from upath import UPath

# All the familiar pathlib operations
path = UPath("s3://bucket/data/file.txt")

print(path.name)        # "file.txt"
print(path.stem)        # "file"
print(path.suffix)      # ".txt"
print(path.parent)      # UPath("s3://bucket/data")

# Path joining
output = path.parent / "processed" / "output.csv"

# File operations
path.write_text("Hello!")
content = path.read_text()

# Directory operations
for item in path.parent.iterdir():
    print(item)
```

!!! tip "Zero Learning Curve"
    Your existing pathlib knowledge transfers directly. No new concepts to learn, no cognitive overhead!

### 2. Write Once, Run Anywhere :earth_americas:

Change storage backends without changing code:

=== "Development (Local)"

    ```python
    from upath import UPath

    def process_data(input_path: str, output_path: str):
        data_file = UPath(input_path)
        result_file = UPath(output_path)

        # Read, process, write
        data = data_file.read_text()
        processed = data.upper()
        result_file.write_text(processed)

    # Local development
    process_data("data/input.txt", "data/output.txt")
    ```

=== "Production (S3)"

    ```python
    from upath import UPath

    def process_data(input_path: str, output_path: str):
        data_file = UPath(input_path)
        result_file = UPath(output_path)

        # Same code! Just different paths
        data = data_file.read_text()
        processed = data.upper()
        result_file.write_text(processed)

    # Production on S3
    process_data(
        "s3://my-bucket/data/input.txt",
        "s3://my-bucket/data/output.txt"
    )
    ```

=== "Testing (Memory)"

    ```python
    from upath import UPath

    def process_data(input_path: str, output_path: str):
        data_file = UPath(input_path)
        result_file = UPath(output_path)

        # Same code! No mocking needed
        data = data_file.read_text()
        processed = data.upper()
        result_file.write_text(processed)

    # Fast tests with in-memory filesystem
    process_data(
        "memory://input.txt",
        "memory://output.txt"
    )
    ```

!!! success "Truly Portable Code"
    Your business logic stays clean and your application does not have to
    care about where the files live anymore.

### 3. Type-Safe and IDE-Friendly :computer:

Universal Pathlib includes type hints for excellent IDE support:

```python
from upath import UPath
from pathlib import Path

def process_file(path: UPath | Path) -> str:
    # Your IDE knows about all methods!
    if path.exists():               # ✓ Autocomplete
        content = path.read_text()  # ✓ Type checked
        return content.upper()
    return ""

# Works with both!
local_result = process_file(UPath("file.txt"))
s3_result = process_file(UPath("s3://bucket/file.txt"))
```

!!! info "Editor Support"
    Get autocomplete, type checking, and inline documentation in VS Code, PyCharm, and other modern Python IDEs.

### 4. Extensively Tested :test_tube:

Universal Pathlib runs a large subset of CPython's pathlib test suite:

- :white_check_mark: **Compatibility tested** against standard library pathlib
- :white_check_mark: **Cross-version tested** on Python 3.9-3.14
- :white_check_mark: **Integration tested** with real filesystems
- :white_check_mark: **Regression tested** for each release

!!! quote "Extensively Tested"
    When we say "pathlib-compatible," we mean it.

### 5. Extensible and Future-Proof :rocket:

Built on `fsspec`, the standard for Python filesystem abstractions:

```python
# Works with many fsspec filesystems!
UPath("s3://...", anon=True)
UPath("gs://...", token='anon')
UPath("az://...")
UPath("https://...")
```

Need a custom filesystem? Implement it once with fsspec, and UPath works automatically!

!!! tip "Ecosystem Benefits"
    Leverage the entire fsspec ecosystem: caching, compression, callback hooks, and more!

---

## Next Steps :footprints:

Ready to give Universal Pathlib a try?

1. **[Install Universal Pathlib](install.md)** - Get set up in minutes
2. **[Understand the concepts](concepts/index.md)** - Understand the concepts
3. **[Read the API docs](api/index.md)** - Learn about all the features

<div align="center" markdown>

[Install Now →](install.md){ .md-button .md-button--primary }

</div>
