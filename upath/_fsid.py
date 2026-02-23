"""Filesystem identity (fsid) fallback computation.

This module provides `_fallback_fsid` to compute filesystem identity from
protocol, storage_options, and fsspec global config (`fsspec.config.conf`)
without instantiating the filesystem.

The fsid is used by __eq__, relative_to, and is_relative_to to determine
if two paths are on the same filesystem. The key insight is that many
storage_options (like authentication or performance settings) don't affect
*which* filesystem is being accessed, only *how* it's accessed.

For filesystems where fsid cannot be determined (e.g., memory filesystem,
unknown protocols), returns None and callers fall back to comparing
storage_options directly.
"""

from __future__ import annotations

from collections import ChainMap
from collections.abc import Mapping
from typing import Any

from fsspec.config import conf as fsspec_conf
from fsspec.utils import tokenize

__all__ = ["_fallback_fsid"]


def _fallback_fsid(protocol: str, storage_options: Mapping[str, Any]) -> str | None:
    """Compute fsid from protocol, storage_options, and fsspec global config."""
    global_opts = fsspec_conf.get(protocol)
    opts: Mapping[str, Any] = (
        ChainMap(storage_options, global_opts)  # type: ignore[arg-type]
        if global_opts
        else storage_options
    )

    match protocol:
        # Static fsid (no instance attributes needed)
        case "" | "file" | "local":
            return "local"
        case "http" | "https":
            return "http"
        case "memory" | "memfs":
            return None  # Non-durable, fall back to storage_options
        case "data":
            return None  # Non-durable

        # Host + port based
        case "sftp" | "ssh":
            host = opts.get("host", "")
            port = opts.get("port", 22)
            return f"sftp_{tokenize(host, port)}" if host else None
        case "smb":
            host = opts.get("host", "")
            port = opts.get("port", 445)
            return f"smb_{tokenize(host, port)}" if host else None
        case "ftp":
            host = opts.get("host", "")
            port = opts.get("port", 21)
            return f"ftp_{tokenize(host, port)}" if host else None
        case "webhdfs" | "webHDFS":
            host = opts.get("host", "")
            port = opts.get("port", 50070)
            return f"webhdfs_{tokenize(host, port)}" if host else None

        # Cloud object storage
        case "s3" | "s3a":
            endpoint = opts.get("endpoint_url", "https://s3.amazonaws.com")
            # Normalize AWS endpoints
            from urllib.parse import urlparse

            parsed = urlparse(endpoint)
            if parsed.netloc.endswith(".amazonaws.com"):
                return "s3_aws"
            return f"s3_{tokenize(endpoint)}"
        case "gcs" | "gs":
            return "gcs"  # Single global endpoint
        case "abfs" | "az":
            account = opts.get("account_name", "")
            return f"abfs_{tokenize(account)}" if account else None
        case "adl":
            tenant = opts.get("tenant_id", "")
            store = opts.get("store_name", "")
            return f"adl_{tokenize(tenant, store)}" if tenant and store else None
        case "oci":
            region = opts.get("region", "")
            return f"oci_{tokenize(region)}" if region else None
        case "oss":
            endpoint = opts.get("endpoint", "")
            return f"oss_{tokenize(endpoint)}" if endpoint else None

        # Git-based
        case "git":
            path = opts.get("path", "")
            ref = opts.get("ref", "")
            return f"git_{tokenize(path, ref)}" if path else None
        case "github":
            org = opts.get("org", "")
            repo = opts.get("repo", "")
            sha = opts.get("sha", "")
            return f"github_{tokenize(org, repo, sha)}" if org and repo else None

        # Platform-specific
        case "hf":
            endpoint = opts.get("endpoint", "huggingface.co")
            return f"hf_{tokenize(endpoint)}"
        case "lakefs":
            host = opts.get("host", "")
            return f"lakefs_{tokenize(host)}" if host else None
        case "webdav":
            base_url = opts.get("base_url", "")
            return f"webdav_{tokenize(base_url)}" if base_url else None
        case "box":
            return "box"
        case "dropbox":
            return "dropbox"

        # Wrappers - delegate to underlying
        case "simplecache" | "filecache" | "blockcache" | "cached":
            return None  # Complex, fall back

        # Archive filesystems - need underlying fs info
        case "zip" | "tar":
            return None  # Complex, fall back

        # Default: unknown protocol, fall back to storage_options
        case _:
            return None
