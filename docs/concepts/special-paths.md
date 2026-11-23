# Special Paths :compass:

Pathlib users have a precise intuition for `Path("")`, `Path(".")`, `Path("..")` and `Path("/")`.
Universal pathlib supports many very different backends though, and not all of these concepts
translate one-to-one: object stores have no directories and no working directory, URLs care
about trailing slashes, and some paths can't be joined at all.

This page defines what the special path segments `""`, `"."`, `".."`, `"/"`, a trailing `"/"`
and an empty segment (`"a//b"`) mean for `UPath`, and which behavior you can rely on across
backends. The behavior described here is covered by the test suite
(`upath/tests/test_special_paths.py`).

## Four kinds of paths

Every `UPath` falls into one of four categories. The category determines what the anchor
(drive + root) of a path is, and how special segments are interpreted.

| Category | Protocols | Example | Anchor |
|---|---|---|---|
| **(a) pathlib-backed local paths** | no protocol | `UPath("/tmp/a")` | `"/"` (or `"C:\\"`) |
| **(b) rooted fsspec paths** | `memory`, `file`, `sftp`, `smb`, `ftp`, `hdfs`, `webdav`, `github`, `hf`, `zip`, `tar`, ... | `UPath("memory:///a")` | the filesystem root: `"/"` or `""` |
| **(c) anchored fsspec paths** | `s3`, `gcs`/`gs`, `az`/`abfs`/`adl`, `http`/`https` | `UPath("s3://bucket/a")` | the bucket, container or host: `"bucket/"`, `"https://host/"` |
| **(d) non-joinable paths** | `data` | `UPath("data:text/plain,hi")` | `""` |

**(a)** `PosixUPath` and `WindowsUPath` are subclasses of `pathlib.Path` and behave exactly like
it. **(b)** and **(c)** are backed by an fsspec filesystem. The difference between them is that
category (c) filesystems have many independent roots (one per bucket or host), so the bucket is
part of the anchor and `..` can never leave it. Category (b) filesystems have a single root
marker, which is either `"/"` (e.g. `memory`, `file`, `sftp`) or `""` (e.g. `zip`, `github`, `hf`).

## Quick reference

Joining special segments onto the root of a filesystem:

| Expression | (a) `root = UPath("/")` | (b) `root = UPath("memory:///")` | (c) `root = UPath("s3://bucket/")` |
|---|---|---|---|
| `root / ""` | `/` | `memory://` | `s3://bucket/` |
| `root / "."` | `/` | `memory://.` | `s3://bucket/.` |
| `root / ".."` | `/..` | `memory://..` | `s3://bucket/..` |
| `(root / "..").resolve()` | `/` | `memory://` | `s3://bucket/` |
| `root / "a/./b"` | `/a/b` | `memory://a/./b` | `s3://bucket/a/./b` |
| `(root / "a/./b").resolve()` | `/a/b` | `memory://a/b` | `s3://bucket/a/b` |
| `root / "a/"` | `/a` | `memory://a` | `s3://bucket/a` |
| `root / "a//b"` | `/a/b` | `memory://a//b` | `s3://bucket/a//b` |

And constructing paths from special strings:

| Expression | (a) no protocol | (b) `protocol="memory"` | (c) `protocol="s3"` |
|---|---|---|---|
| `UPath("", ...)` | `.` (current directory) | `memory://` (the root) | `s3://` (no bucket) |
| `UPath(".", ...)` | `.` (current directory) | `memory://.` | _don't_: `"."` is parsed as a bucket name |
| `UPath("..", ...)` | `..` (relative) | `memory://..` | _don't_: `".."` is parsed as a bucket name |
| `UPath("/", ...)` | `/` (the root) | `memory://` (the root) | `s3://` (no bucket) |

## Guarantees for all joinable paths

These hold for categories (a), (b) and (c):

1. **Joining an empty segment is a no-op:** `p / "" == p`.
   _Exception:_ on `http`/`https`, where a trailing slash is meaningful, an empty final segment
   is a trailing slash: `UPath("https://example.com/a") / ""` is `https://example.com/a/`.
2. **`..` is a regular segment until you resolve the path:** `p / "a" / ".."` has the name
   `".."` and its parent is `p / "a"`. This is true for `pathlib` too, because on a real
   filesystem `a/..` might not be the same as `.` if `a` is a symlink.
3. **`resolve()` interprets `.` and `..`**: the result contains no `.` or `..` segments, and
   `..` never goes above the anchor: `(root / "..").resolve() == root`.
   For fsspec-backed paths `resolve()` is purely lexical (no filesystem access), with one
   exception: `HTTPPath.resolve()` follows redirects unless called with
   `follow_redirects=False`. For local paths `resolve()` is `pathlib.Path.resolve()`, which
   makes the path absolute and resolves symlinks.
4. **Trailing slashes are not significant:** `p / "a/" == p / "a"`, except on `http`/`https`.
5. **The anchor is its own parent:** `root.parent == root`, and `(root / "a").parent == root`.

```pycon
>>> from upath import UPath
>>> root = UPath("memory:///")
>>> root / "" == root
True
>>> p = root / "a" / ".."
>>> p, p.name, p.parent
(MemoryPath('/a/..', protocol='memory'), '..', MemoryPath('/a', protocol='memory'))
>>> p.resolve() == root
True
>>> (root / "a/./b/../c").resolve()
MemoryPath('/a/c', protocol='memory')
```

## (a) pathlib-backed local paths

`UPath(...)` without a protocol returns a `PosixUPath` or `WindowsUPath`, and all special paths
behave exactly as they do for `pathlib.Path`:

- `UPath("")` and `UPath(".")` are the same relative path, the current working directory.
- `UPath("..")` is a relative path to the parent of the current working directory.
- `UPath("/")` is the root (on Windows it is the root of the current drive and not absolute).
- `.` segments and repeated slashes are dropped during construction, `..` segments are kept.

```pycon
>>> from pathlib import Path
>>> UPath("") == UPath(".") == UPath(Path("."))
True
>>> UPath("a/./b//c/../")
PosixUPath('a/b/c/..')
```

## fsspec-backed paths: no working directory, always absolute

fsspec filesystems have no concept of a current working directory, and the paths they accept
are always absolute. This has a few consequences for categories (b) and (c):

- **Every fsspec-backed `UPath` is absolute.** Relative `UPath` instances can only be created via
  `relative_to()`.
- **The empty path is the root.** `UPath("", protocol="memory")` and `UPath("/", protocol="memory")`
  both denote the root of the memory filesystem. For anchored filesystems
  `UPath("", protocol="s3")` is `s3://`, a path without a bucket. Joining a bucket name onto it
  gives the bucket root.
- **Relative strings are relative to the root.** `UPath("a", protocol="memory")` is
  `memory:///a`. The exception is `file`/`local`, where fsspec's `LocalFileSystem` makes relative
  strings absolute using the current working directory at construction time:
  `UPath("", protocol="file")` and `UPath(".", protocol="file")` are the current working
  directory.
- **`.` and `..` are kept verbatim.** UPath does not normalize `.` or `..` segments when
  constructing or joining fsspec-backed paths. Many backends allow these as regular names
  (`a/./b` and `a/b` are two different keys in an S3 bucket or in the memory filesystem), so
  normalizing them would make objects unreachable. Use `.resolve()` to get the POSIX
  interpretation.

```pycon
>>> UPath("", protocol="memory") == UPath("/", protocol="memory") == UPath("memory:///")
True
>>> UPath(".", protocol="memory")
MemoryPath('/.', protocol='memory')
>>> UPath(".", protocol="memory") == UPath("", protocol="memory")
False
>>> UPath(".", protocol="memory").resolve() == UPath("", protocol="memory")
True
>>> UPath("a", protocol="memory") == UPath("memory:///a")
True
>>> UPath("", protocol="s3") / "bucket" == UPath("s3://bucket/")
True
```

!!! tip "Interpreting `.` and `..` like pathlib"
    If your code builds paths from user input or from relative locations that may contain `.`
    or `..`, call `.resolve()` before accessing the filesystem. For fsspec-backed paths this
    is a cheap, purely lexical operation.

    ```pycon
    >>> (UPath("s3://bucket/data") / "../config/./settings.json").resolve()
    S3Path('bucket/config/settings.json', protocol='s3')
    ```

## (b) Rooted fsspec paths

Filesystems in this category have a single root, given by the filesystem's root marker:

- root marker `"/"`: `memory`, `file`, `sftp`, `smb`, `ftp`, `hdfs`. The anchor is `"/"`.
- root marker `""`: `zip`, `tar`, `github`, `webdav`, `hf`. The anchor is `""` and the parts
  of a path don't start with a root element.

On these filesystems, joining a segment that starts with `"/"` restarts at the root, just like
`pathlib`: `UPath("memory:///a") / "/b" == UPath("memory:///b")`.

Repeated slashes (`"a//b"`) are kept in the path string and passed to the filesystem as-is.
Whether `a//b` refers to the same object as `a/b` depends on the backend, so don't rely on it.

## (c) Anchored fsspec paths

For `s3`, `gcs`, `az` and `http(s)`, the bucket, container or host is part of the anchor:

```pycon
>>> p = UPath("s3://bucket/a/b")
>>> p.drive, p.root, p.anchor, p.parts
('bucket', '/', 'bucket/', ('bucket/', 'a', 'b'))
>>> (p / "../../..").resolve()
S3Path('bucket/', protocol='s3')
```

These filesystems support **empty parts**: object keys may contain repeated slashes, so
`UPath("s3://bucket/a//b")` and `UPath("s3://bucket/a/b")` are different paths.

`http` and `https` paths additionally have a **meaningful trailing slash**:
`UPath("https://example.com/a/")` and `UPath("https://example.com/a")` are different URLs, and
`resolve()` normalizes dot segments following RFC 3986. Use `UPath.joinuri()` if you need
URL-join semantics (where `"/b"` or `"../b"` are resolved relative to the base URL).

## (d) Non-joinable paths

A `DataPath` (`data:` URI) contains its data in the path itself. It has no parent, no
children and no meaningful segments: `p.parent == p`, `p.parts == (p.path,)`, and joining
anything onto it raises `UnsupportedOperation`.

## Writing backend-agnostic code

- Construct paths from a full URI or a root path and join segments onto it, instead of passing
  `""`, `"."` or `".."` together with `protocol=`.
- Call `.resolve()` before filesystem access if a path may contain `.` or `..` segments.
- Avoid trailing slashes and empty segments, unless you work with `http(s)` URLs where they
  matter.
- Keep relative locations as `pathlib.PurePosixPath` instances and join them onto a `UPath`
  base when needed.

!!! warning "Known deviations"
    A few implementations currently deviate from the behavior described above. They are
    tracked as expected failures in `upath/tests/test_special_paths.py` and may change in a
    future release:

    - `sftp`, `smb`, `hdfs`: relative strings given with `protocol=` are not rooted, e.g.
      `UPath("a", protocol="sftp")` is not absolute.
    - `github`, `webdav`: `resolve()` does not fully normalize `..` segments.
    - `webdav`: URIs keep a leading `/` in `.path`; `github`: URIs keep a trailing `/` in `.path`.
    - `zip`, `tar`, `hf`: `.parts` starts with `"/"` although the anchor is `""`.
    - `github`, `webdav`, `hf`, `tar`: joining a segment starting with `"/"` keeps the `"/"`.
    - `s3`, `gcs`, `az`: `.parts` drops empty segments.
    - `hdfs`: trailing slashes are kept.
