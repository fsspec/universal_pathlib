"""Static checks for UPath constructor type narrowing.

This file is not executed. It is checked with mypy, pyright and ty via
`nox -s type-narrowing` to ensure that all supported type checkers infer
the same types when constructing UPath instances.
"""

from __future__ import annotations

import sys
from typing import Any

from typing_extensions import assert_type

from upath import UPath
from upath.extensions import ProxyUPath
from upath.implementations.cached import SimpleCachePath
from upath.implementations.cloud import AzurePath
from upath.implementations.cloud import GCSPath
from upath.implementations.cloud import HfPath
from upath.implementations.cloud import S3Path
from upath.implementations.data import DataPath
from upath.implementations.ftp import FTPPath
from upath.implementations.github import GitHubPath
from upath.implementations.hdfs import HDFSPath
from upath.implementations.http import HTTPPath
from upath.implementations.local import FilePath
from upath.implementations.local import PosixUPath
from upath.implementations.local import WindowsUPath
from upath.implementations.memory import MemoryPath
from upath.implementations.sftp import SFTPPath
from upath.implementations.smb import SMBPath
from upath.implementations.tar import TarPath
from upath.implementations.webdav import WebdavPath
from upath.implementations.zip import ZipPath
from upath.registry import get_upath_class


class MyProxyUPath(ProxyUPath):
    pass


def check_upath_without_protocol() -> None:
    assert_type(UPath(), UPath)
    assert_type(UPath("s3://bucket/key"), UPath)
    assert_type(UPath("memory:///a"), UPath)
    assert_type(UPath("/some/local/path"), UPath)


def check_upath_with_protocol(protocol: str, kw: dict[str, Any]) -> None:
    assert_type(UPath("bucket/key", protocol="s3", anon=True), S3Path)
    assert_type(UPath("bucket/key", protocol="s3", **kw), S3Path)
    assert_type(UPath("bucket/key", protocol="s3").parent, S3Path)
    assert_type(UPath("a", protocol="unknown-protocol"), UPath)
    assert_type(UPath("a", protocol=protocol), UPath)
    if sys.platform == "win32":
        assert_type(UPath("a", protocol=""), WindowsUPath)
    else:
        assert_type(UPath("a", protocol=""), PosixUPath)


def check_upath_protocol_literals() -> None:
    assert_type(UPath("a", protocol="simplecache"), SimpleCachePath)
    assert_type(UPath("a", protocol="gcs"), GCSPath)
    assert_type(UPath("a", protocol="gs"), GCSPath)
    assert_type(UPath("a", protocol="s3"), S3Path)
    assert_type(UPath("a", protocol="s3a"), S3Path)
    assert_type(UPath("a", protocol="az"), AzurePath)
    assert_type(UPath("a", protocol="abfs"), AzurePath)
    assert_type(UPath("a", protocol="abfss"), AzurePath)
    assert_type(UPath("a", protocol="adl"), AzurePath)
    assert_type(UPath("a", protocol="hf"), HfPath)
    assert_type(UPath("a", protocol="data"), DataPath)
    assert_type(UPath("a", protocol="ftp"), FTPPath)
    assert_type(UPath("a", protocol="github"), GitHubPath)
    assert_type(UPath("a", protocol="hdfs"), HDFSPath)
    assert_type(UPath("a", protocol="http"), HTTPPath)
    assert_type(UPath("a", protocol="https"), HTTPPath)
    assert_type(UPath("a", protocol="file"), FilePath)
    assert_type(UPath("a", protocol="local"), FilePath)
    assert_type(UPath("a", protocol="memory"), MemoryPath)
    assert_type(UPath("a", protocol="sftp"), SFTPPath)
    assert_type(UPath("a", protocol="ssh"), SFTPPath)
    assert_type(UPath("a", protocol="smb"), SMBPath)
    assert_type(UPath("a", protocol="tar"), TarPath)
    assert_type(UPath("a", protocol="webdav"), WebdavPath)
    assert_type(UPath("a", protocol="webdav+http"), WebdavPath)
    assert_type(UPath("a", protocol="webdav+https"), WebdavPath)
    assert_type(UPath("a", protocol="zip"), ZipPath)


def check_upath_subclasses() -> None:
    assert_type(S3Path("s3://bucket/key"), S3Path)
    assert_type(S3Path("s3://bucket/key", anon=True), S3Path)
    assert_type(MemoryPath("memory:///a"), MemoryPath)
    assert_type(FilePath("/a"), FilePath)
    assert_type(MyProxyUPath("memory:///a"), MyProxyUPath)


def check_get_upath_class() -> None:
    assert_type(get_upath_class("s3"), "type[S3Path]")
    assert_type(get_upath_class("s3")("bucket/key", anon=True), S3Path)
    assert_type(get_upath_class("webdav+https"), "type[WebdavPath]")
    assert_type(get_upath_class("unknown-protocol"), "type[UPath] | None")
