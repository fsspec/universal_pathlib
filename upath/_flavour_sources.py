""" upath._flavour_sources

<experimental!>

Warning
-------
  Do not modify this file manually!
  It is generated by `dev/generate_flavours.py`

To be able to parse the different filesystem uri schemes, we need
the string parsing functionality each of the filesystem implementations.
In an attempt to support parsing uris without having to import the
specific filesystems, we extract the necessary subset of the
AbstractFileSystem classes and generate a new "flavour" class for
each of the known filesystems. This will allow us to provide a
`PurePath` equivalent `PureUPath` for each protocol in the future
without a direct dependency on the underlying filesystem package.

"""
#
# skipping protocols:
#   - blockcache
#   - cached
#   - dir
#   - filecache
#   - simplecache
# protocol import errors:
#   - async_wrapper (None)
#   - gdrive (Please install gdrivefs for access to Google Drive)
#   - generic (GenericFileSystem: '_strip_protocol' not a classmethod)
#   - tosfs (Install tosfs to access ByteDance volcano engine Tinder Object Storage)
#
from __future__ import annotations

import logging
import os
import re
from pathlib import PurePath
from pathlib import PureWindowsPath
from typing import Any
from typing import Literal
from typing import cast
from urllib.parse import parse_qs
from urllib.parse import urlsplit

from fsspec.implementations.local import make_path_posix
from fsspec.utils import infer_storage_options
from fsspec.utils import stringify_path

__all__ = [
    "AbstractFileSystemFlavour",
    "FileSystemFlavourBase",
    "flavour_registry",
]

logger = logging.getLogger(__name__)
flavour_registry: dict[str, type[FileSystemFlavourBase]] = {}


class FileSystemFlavourBase:
    """base class for the fsspec flavours"""

    protocol: str | tuple[str, ...]
    root_marker: Literal["/", ""]
    sep: Literal["/"]

    @classmethod
    def _strip_protocol(cls, path):
        raise NotImplementedError

    @staticmethod
    def _get_kwargs_from_urls(path):
        raise NotImplementedError

    @classmethod
    def _parent(cls, path):
        raise NotImplementedError

    def __init_subclass__(cls: Any, **kwargs):
        if isinstance(cls.protocol, str):
            protocols = (cls.protocol,)
        else:
            protocols = tuple(cls.protocol)
        for protocol in protocols:
            if protocol in flavour_registry:
                raise ValueError(f"protocol {protocol!r} already registered")
            flavour_registry[protocol] = cls


class AbstractFileSystemFlavour(FileSystemFlavourBase):
    __orig_class__ = 'fsspec.spec.AbstractFileSystem'
    __orig_version__ = '2025.3.2'
    protocol: str | tuple[str, ...] = 'abstract'
    root_marker: Literal['', '/'] = ''
    sep: Literal['/'] = '/'

    @classmethod
    def _strip_protocol(cls, path):
        """Turn path from fully-qualified to file-system-specific

        May require FS-specific handling, e.g., for relative paths or links.
        """
        if isinstance(path, list):
            return [cls._strip_protocol(p) for p in path]
        path = stringify_path(path)
        protos = (cls.protocol,) if isinstance(cls.protocol, str) else cls.protocol
        for protocol in protos:
            if path.startswith(protocol + "://"):
                path = path[len(protocol) + 3 :]
            elif path.startswith(protocol + "::"):
                path = path[len(protocol) + 2 :]
        path = path.rstrip("/")
        # use of root_marker to make minimum required path, e.g., "/"
        return path or cls.root_marker

    @staticmethod
    def _get_kwargs_from_urls(path):
        """If kwargs can be encoded in the paths, extract them here

        This should happen before instantiation of the class; incoming paths
        then should be amended to strip the options in methods.

        Examples may look like an sftp path "sftp://user@host:/my/path", where
        the user and host should become kwargs and later get stripped.
        """
        # by default, nothing happens
        return {}

    @classmethod
    def _parent(cls, path):
        path = cls._strip_protocol(path)
        if "/" in path:
            parent = path.rsplit("/", 1)[0].lstrip(cls.root_marker)
            return cls.root_marker + parent
        else:
            return cls.root_marker


class AsyncLocalFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'morefs.asyn_local.AsyncLocalFileSystem'
    __orig_version__ = '0.2.2'
    protocol = ()
    root_marker = '/'
    sep = '/'
    local_file = True

    @classmethod
    def _strip_protocol(cls, path):
        path = stringify_path(path)
        if path.startswith("file://"):
            path = path[7:]
        elif path.startswith("file:"):
            path = path[5:]
        elif path.startswith("local://"):
            path = path[8:]
        elif path.startswith("local:"):
            path = path[6:]

        path = make_path_posix(path)
        if os.sep != "/":
            # This code-path is a stripped down version of
            # > drive, path = ntpath.splitdrive(path)
            if path[1:2] == ":":
                # Absolute drive-letter path, e.g. X:\Windows
                # Relative path with drive, e.g. X:Windows
                drive, path = path[:2], path[2:]
            elif path[:2] == "//":
                # UNC drives, e.g. \\server\share or \\?\UNC\server\share
                # Device drives, e.g. \\.\device or \\?\device
                if (index1 := path.find("/", 2)) == -1 or (
                    index2 := path.find("/", index1 + 1)
                ) == -1:
                    drive, path = path, ""
                else:
                    drive, path = path[:index2], path[index2:]
            else:
                # Relative path, e.g. Windows
                drive = ""

            path = path.rstrip("/") or cls.root_marker
            return drive + path

        else:
            return path.rstrip("/") or cls.root_marker

    @classmethod
    def _parent(cls, path):
        path = cls._strip_protocol(path)
        if os.sep == "/":
            # posix native
            return path.rsplit("/", 1)[0] or "/"
        else:
            # NT
            path_ = path.rsplit("/", 1)[0]
            if len(path_) <= 3:
                if path_[1:2] == ":":
                    # nt root (something like c:/)
                    return path_[0] + ":/"
            # More cases may be required here
            return path_


class AzureBlobFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'adlfs.spec.AzureBlobFileSystem'
    __orig_version__ = '2024.12.0'
    protocol = ('abfs', 'az', 'abfss')
    root_marker = ''
    sep = '/'

    @classmethod
    def _strip_protocol(cls, path: str):
        """
        Remove the protocol from the input path

        Parameters
        ----------
        path: str
            Path to remove the protocol from

        Returns
        -------
        str
            Returns a path without the protocol
        """
        if isinstance(path, list):  # type: ignore[unreachable]
            return [cls._strip_protocol(p) for p in path]  # type: ignore[unreachable]

        STORE_SUFFIX = ".dfs.core.windows.net"
        logger.debug(f"_strip_protocol for {path}")
        if not path.startswith(("abfs://", "az://", "abfss://")):
            path = path.lstrip("/")
            path = "abfs://" + path
        ops = infer_storage_options(path)
        if "username" in ops:
            if ops.get("username", None):
                ops["path"] = ops["username"] + ops["path"]
        # we need to make sure that the path retains
        # the format {host}/{path}
        # here host is the container_name
        elif ops.get("host", None):
            if (
                ops["host"].count(STORE_SUFFIX) == 0
            ):  # no store-suffix, so this is container-name
                ops["path"] = ops["host"] + ops["path"]
        url_query = ops.get("url_query")
        if url_query is not None:
            ops["path"] = f"{ops['path']}?{url_query}"

        logger.debug(f"_strip_protocol({path}) = {ops}")
        stripped_path = ops["path"].lstrip("/")
        return stripped_path

    @staticmethod
    def _get_kwargs_from_urls(urlpath):
        """Get the account_name from the urlpath and pass to storage_options"""
        ops = infer_storage_options(urlpath)
        out = {}
        host = ops.get("host", None)
        if host:
            match = re.match(
                r"(?P<account_name>.+)\.(dfs|blob)\.core\.windows\.net", host
            )
            if match:
                account_name = match.groupdict()["account_name"]
                out["account_name"] = account_name
        url_query = ops.get("url_query")
        if url_query is not None:
            from urllib.parse import parse_qs

            parsed = parse_qs(url_query)
            if "versionid" in parsed:
                out["version_aware"] = True
        return out


class AzureDatalakeFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'adlfs.gen1.AzureDatalakeFileSystem'
    __orig_version__ = '2024.12.0'
    protocol = ('adl',)
    root_marker = ''
    sep = '/'

    @classmethod
    def _strip_protocol(cls, path):
        ops = infer_storage_options(path)
        return ops["path"]

    @staticmethod
    def _get_kwargs_from_urls(paths):
        """Get the store_name from the urlpath and pass to storage_options"""
        ops = infer_storage_options(paths)
        out = {}
        if ops.get("host", None):
            out["store_name"] = ops["host"]
        return out


class BoxFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'boxfs.boxfs.BoxFileSystem'
    __orig_version__ = '0.3.0'
    protocol = ('box',)
    root_marker = '/'
    sep = '/'

    @classmethod
    def _strip_protocol(cls, path) -> str:
        path = super()._strip_protocol(path)
        path = path.replace("\\", "/")
        # Make all paths start with root marker
        if not path.startswith(cls.root_marker):
            path = cls.root_marker + path
        return path


class DaskWorkerFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'fsspec.implementations.dask.DaskWorkerFileSystem'
    __orig_version__ = '2025.3.2'
    protocol = ('dask',)
    root_marker = ''
    sep = '/'

    @staticmethod
    def _get_kwargs_from_urls(path):
        so = infer_storage_options(path)
        if "host" in so and "port" in so:
            return {"client": f"{so['host']}:{so['port']}"}
        else:
            return {}


class DataFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'fsspec.implementations.data.DataFileSystem'
    __orig_version__ = '2025.3.2'
    protocol = ('data',)
    root_marker = ''
    sep = '/'


class DatabricksFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'fsspec.implementations.dbfs.DatabricksFileSystem'
    __orig_version__ = '2025.3.2'
    protocol = ('dbfs',)
    root_marker = ''
    sep = '/'


class DictFSFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'morefs.dict.DictFS'
    __orig_version__ = '0.2.2'
    protocol = ('dictfs',)
    root_marker = ''
    sep = '/'

    @classmethod
    def _strip_protocol(cls, path: str) -> str:
        if path.startswith("dictfs://"):
            path = path[len("dictfs://") :]
        if "::" in path or "://" in path:
            return path.rstrip("/")
        path = path.lstrip("/").rstrip("/")
        return "/" + path if path else cls.root_marker


class DropboxDriveFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'dropboxdrivefs.core.DropboxDriveFileSystem'
    __orig_version__ = '1.4.1'
    protocol = ('dropbox',)
    root_marker = ''
    sep = '/'


class FTPFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'fsspec.implementations.ftp.FTPFileSystem'
    __orig_version__ = '2025.3.2'
    protocol = ('ftp',)
    root_marker = '/'
    sep = '/'

    @classmethod
    def _strip_protocol(cls, path):
        return "/" + infer_storage_options(path)["path"].lstrip("/").rstrip("/")

    @staticmethod
    def _get_kwargs_from_urls(urlpath):
        out = infer_storage_options(urlpath)
        out.pop("path", None)
        out.pop("protocol", None)
        return out


class GCSFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'gcsfs.core.GCSFileSystem'
    __orig_version__ = '2025.3.2'
    protocol = ('gs', 'gcs')
    root_marker = ''
    sep = '/'

    @classmethod
    def _strip_protocol(cls, path):
        if isinstance(path, list):
            return [cls._strip_protocol(p) for p in path]
        path = stringify_path(path)
        protos = (cls.protocol,) if isinstance(cls.protocol, str) else cls.protocol
        for protocol in protos:
            if path.startswith(protocol + "://"):
                path = path[len(protocol) + 3 :]
            elif path.startswith(protocol + "::"):
                path = path[len(protocol) + 2 :]
        # use of root_marker to make minimum required path, e.g., "/"
        return path or cls.root_marker

    @classmethod
    def _get_kwargs_from_urls(cls, path):
        _, _, generation = cls._split_path(path, version_aware=True)
        if generation is not None:
            return {"version_aware": True}
        return {}

    @classmethod
    def _split_path(cls, path, version_aware=False):
        """
        Normalise GCS path string into bucket and key.

        Parameters
        ----------
        path : string
            Input path, like `gcs://mybucket/path/to/file`.
            Path is of the form: '[gs|gcs://]bucket[/key][?querystring][#fragment]'

        GCS allows object generation (object version) to be specified in either
        the URL fragment or the `generation` query parameter. When provided,
        the fragment will take priority over the `generation` query paramenter.

        Returns
        -------
            (bucket, key, generation) tuple
        """
        path = cls._strip_protocol(path).lstrip("/")
        if "/" not in path:
            return path, "", None
        bucket, keypart = path.split("/", 1)
        key = keypart
        generation = None
        if version_aware:
            parts = urlsplit(keypart)
            try:
                if parts.fragment:
                    generation = parts.fragment
                elif parts.query:
                    parsed = parse_qs(parts.query)
                    if "generation" in parsed:
                        generation = parsed["generation"][0]
                # Sanity check whether this could be a valid generation ID. If
                # it is not, assume that # or ? characters are supposed to be
                # part of the object name.
                if generation is not None:
                    int(generation)
                    key = parts.path
            except ValueError:
                generation = None
        return (
            bucket,
            key,
            generation,
        )


class GitFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'fsspec.implementations.git.GitFileSystem'
    __orig_version__ = '2025.3.2'
    protocol = ('git',)
    root_marker = ''
    sep = '/'

    @classmethod
    def _strip_protocol(cls, path):
        path = super()._strip_protocol(path).lstrip("/")
        if ":" in path:
            path = path.split(":", 1)[1]
        if "@" in path:
            path = path.split("@", 1)[1]
        return path.lstrip("/")

    @staticmethod
    def _get_kwargs_from_urls(path):
        if path.startswith("git://"):
            path = path[6:]
        out = {}
        if ":" in path:
            out["path"], path = path.split(":", 1)
        if "@" in path:
            out["ref"], path = path.split("@", 1)
        return out


class GithubFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'fsspec.implementations.github.GithubFileSystem'
    __orig_version__ = '2025.3.2'
    protocol = ('github',)
    root_marker = ''
    sep = '/'

    @classmethod
    def _strip_protocol(cls, path):
        opts = infer_storage_options(path)
        if "username" not in opts:
            return super()._strip_protocol(path)
        return opts["path"].lstrip("/")

    @staticmethod
    def _get_kwargs_from_urls(path):
        opts = infer_storage_options(path)
        if "username" not in opts:
            return {}
        out = {"org": opts["username"], "repo": opts["password"]}
        if opts["host"]:
            out["sha"] = opts["host"]
        return out


class HTTPFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'fsspec.implementations.http.HTTPFileSystem'
    __orig_version__ = '2025.3.2'
    protocol = ('http', 'https')
    root_marker = ''
    sep = '/'

    @classmethod
    def _strip_protocol(cls, path):
        """For HTTP, we always want to keep the full URL"""
        return path

    @classmethod
    def _parent(cls, path):
        # override, since _strip_protocol is different for URLs
        par = super()._parent(path)
        if len(par) > 7:  # "http://..."
            return par
        return ""


class HadoopFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'fsspec.implementations.arrow.HadoopFileSystem'
    __orig_version__ = '2025.3.2'
    protocol = ('hdfs', 'arrow_hdfs')
    root_marker = '/'
    sep = '/'

    @classmethod
    def _strip_protocol(cls, path):
        ops = infer_storage_options(path)
        path = ops["path"]
        if path.startswith("//"):
            # special case for "hdfs://path" (without the triple slash)
            path = path[1:]
        return path

    @staticmethod
    def _get_kwargs_from_urls(path):
        ops = infer_storage_options(path)
        out = {}
        if ops.get("host", None):
            out["host"] = ops["host"]
        if ops.get("username", None):
            out["user"] = ops["username"]
        if ops.get("port", None):
            out["port"] = ops["port"]
        if ops.get("url_query", None):
            queries = parse_qs(ops["url_query"])
            if queries.get("replication", None):
                out["replication"] = int(queries["replication"][0])
        return out


class HfFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'huggingface_hub.hf_file_system.HfFileSystem'
    __orig_version__ = '0.30.2'
    protocol = ('hf',)
    root_marker = ''
    sep = '/'


class JupyterFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'fsspec.implementations.jupyter.JupyterFileSystem'
    __orig_version__ = '2025.3.2'
    protocol = ('jupyter', 'jlab')
    root_marker = ''
    sep = '/'


class LakeFSFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'lakefs_spec.spec.LakeFSFileSystem'
    __orig_version__ = '0.11.3'
    protocol = ('lakefs',)
    root_marker = ''
    sep = '/'

    @classmethod
    def _strip_protocol(cls, path):
        """Copied verbatim from the base class, save for the slash rstrip."""
        if isinstance(path, list):
            return [cls._strip_protocol(p) for p in path]
        spath = super()._strip_protocol(path)
        if stringify_path(path).endswith("/"):
            return spath + "/"
        return spath


class LibArchiveFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'fsspec.implementations.libarchive.LibArchiveFileSystem'
    __orig_version__ = '2025.3.2'
    protocol = ('libarchive',)
    root_marker = ''
    sep = '/'

    @classmethod
    def _strip_protocol(cls, path):
        # file paths are always relative to the archive root
        return super()._strip_protocol(path).lstrip("/")


class LocalFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'fsspec.implementations.local.LocalFileSystem'
    __orig_version__ = '2025.3.2'
    protocol = ('file', 'local')
    root_marker = '/'
    sep = '/'
    local_file = True

    @classmethod
    def _strip_protocol(cls, path):
        path = stringify_path(path)
        if path.startswith("file://"):
            path = path[7:]
        elif path.startswith("file:"):
            path = path[5:]
        elif path.startswith("local://"):
            path = path[8:]
        elif path.startswith("local:"):
            path = path[6:]

        path = make_path_posix(path)
        if os.sep != "/":
            # This code-path is a stripped down version of
            # > drive, path = ntpath.splitdrive(path)
            if path[1:2] == ":":
                # Absolute drive-letter path, e.g. X:\Windows
                # Relative path with drive, e.g. X:Windows
                drive, path = path[:2], path[2:]
            elif path[:2] == "//":
                # UNC drives, e.g. \\server\share or \\?\UNC\server\share
                # Device drives, e.g. \\.\device or \\?\device
                if (index1 := path.find("/", 2)) == -1 or (
                    index2 := path.find("/", index1 + 1)
                ) == -1:
                    drive, path = path, ""
                else:
                    drive, path = path[:index2], path[index2:]
            else:
                # Relative path, e.g. Windows
                drive = ""

            path = path.rstrip("/") or cls.root_marker
            return drive + path

        else:
            return path.rstrip("/") or cls.root_marker

    @classmethod
    def _parent(cls, path):
        path = cls._strip_protocol(path)
        if os.sep == "/":
            # posix native
            return path.rsplit("/", 1)[0] or "/"
        else:
            # NT
            path_ = path.rsplit("/", 1)[0]
            if len(path_) <= 3:
                if path_[1:2] == ":":
                    # nt root (something like c:/)
                    return path_[0] + ":/"
            # More cases may be required here
            return path_


class MemFSFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'morefs.memory.MemFS'
    __orig_version__ = '0.2.2'
    protocol = ('memfs',)
    root_marker = ''
    sep = '/'

    @classmethod
    def _strip_protocol(cls, path):
        if path.startswith("memfs://"):
            path = path[len("memfs://") :]
        return MemoryFileSystemFlavour._strip_protocol(path)  # pylint: disable=protected-access


class MemoryFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'fsspec.implementations.memory.MemoryFileSystem'
    __orig_version__ = '2025.3.2'
    protocol = ('memory',)
    root_marker = '/'
    sep = '/'

    @classmethod
    def _strip_protocol(cls, path):
        if isinstance(path, PurePath):
            if isinstance(path, PureWindowsPath):
                return LocalFileSystemFlavour._strip_protocol(path)
            else:
                path = stringify_path(path)

        if path.startswith("memory://"):
            path = path[len("memory://") :]
        if "::" in path or "://" in path:
            return path.rstrip("/")
        path = path.lstrip("/").rstrip("/")
        return "/" + path if path else ""


class OCIFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'ocifs.core.OCIFileSystem'
    __orig_version__ = '1.3.2'
    protocol = ('oci', 'ocilake')
    root_marker = ''
    sep = '/'

    @classmethod
    def _strip_protocol(cls, path):
        if isinstance(path, list):
            return [cls._strip_protocol(p) for p in path]
        path = stringify_path(path)
        stripped_path = super()._strip_protocol(path)
        if stripped_path == cls.root_marker and "@" in path:
            return "@" + path.rstrip("/").split("@", 1)[1]
        return stripped_path

    @classmethod
    def _parent(cls, path):
        path = cls._strip_protocol(path.rstrip("/"))
        if "/" in path:
            return cls.root_marker + path.rsplit("/", 1)[0]
        elif "@" in path:
            return cls.root_marker + "@" + path.split("@", 1)[1]
        else:
            raise ValueError(f"the following path does not specify a namespace: {path}")


class OSSFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'ossfs.core.OSSFileSystem'
    __orig_version__ = '2023.12.0'
    protocol = ('oss',)
    root_marker = ''
    sep = '/'

    @classmethod
    def _strip_protocol(cls, path):
        """Turn path from fully-qualified to file-system-specifi
        Parameters
        ----------
        path : Union[str, List[str]]
            Input path, like
            `http://oss-cn-hangzhou.aliyuncs.com/mybucket/myobject`
            `oss://mybucket/myobject`
        Examples
        --------
        >>> _strip_protocol(
            "http://oss-cn-hangzhou.aliyuncs.com/mybucket/myobject"
            )
        ('/mybucket/myobject')
        >>> _strip_protocol(
            "oss://mybucket/myobject"
            )
        ('/mybucket/myobject')
        """
        if isinstance(path, list):
            return [cls._strip_protocol(p) for p in path]
        path_string = stringify_path(path)
        if path_string.startswith("oss://"):
            path_string = path_string[5:]

        parser_re = r"https?://(?P<endpoint>oss.+aliyuncs\.com)(?P<path>/.+)"
        matcher = re.compile(parser_re).match(path_string)
        if matcher:
            path_string = matcher["path"]
        return path_string or cls.root_marker


class OverlayFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'morefs.overlay.OverlayFileSystem'
    __orig_version__ = '0.2.2'
    protocol = ('overlayfs',)
    root_marker = ''
    sep = '/'


class ReferenceFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'fsspec.implementations.reference.ReferenceFileSystem'
    __orig_version__ = '2025.3.2'
    protocol = ('reference',)
    root_marker = ''
    sep = '/'


class S3FileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 's3fs.core.S3FileSystem'
    __orig_version__ = '2025.3.2'
    protocol = ('s3', 's3a')
    root_marker = ''
    sep = '/'

    @staticmethod
    def _get_kwargs_from_urls(urlpath):
        """
        When we have a urlpath that contains a ?versionId=

        Assume that we want to use version_aware mode for
        the filesystem.
        """
        from urllib.parse import urlsplit

        url_query = urlsplit(urlpath).query
        out = {}
        if url_query is not None:
            from urllib.parse import parse_qs

            parsed = parse_qs(url_query)
            if "versionId" in parsed:
                out["version_aware"] = True
        return out


class SFTPFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'fsspec.implementations.sftp.SFTPFileSystem'
    __orig_version__ = '2025.3.2'
    protocol = ('sftp', 'ssh')
    root_marker = ''
    sep = '/'

    @classmethod
    def _strip_protocol(cls, path):
        return infer_storage_options(path)["path"]

    @staticmethod
    def _get_kwargs_from_urls(urlpath):
        out = infer_storage_options(urlpath)
        out.pop("path", None)
        out.pop("protocol", None)
        return out


class SMBFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'fsspec.implementations.smb.SMBFileSystem'
    __orig_version__ = '2025.3.2'
    protocol = ('smb',)
    root_marker = ''
    sep = '/'

    @classmethod
    def _strip_protocol(cls, path):
        return infer_storage_options(path)["path"]

    @staticmethod
    def _get_kwargs_from_urls(path):
        # smb://workgroup;user:password@host:port/share/folder/file.csv
        out = infer_storage_options(path)
        out.pop("path", None)
        out.pop("protocol", None)
        return out


class TarFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'fsspec.implementations.tar.TarFileSystem'
    __orig_version__ = '2025.3.2'
    protocol = ('tar',)
    root_marker = ''
    sep = '/'


class WandbFSFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'wandbfs._wandbfs.WandbFS'
    __orig_version__ = '0.0.2'
    protocol = ('wandb',)
    root_marker = ''
    sep = '/'


class WebHDFSFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'fsspec.implementations.webhdfs.WebHDFS'
    __orig_version__ = '2025.3.2'
    protocol = ('webhdfs', 'webHDFS')
    root_marker = ''
    sep = '/'

    @classmethod
    def _strip_protocol(cls, path):
        return infer_storage_options(path)["path"]

    @staticmethod
    def _get_kwargs_from_urls(urlpath):
        out = infer_storage_options(urlpath)
        out.pop("path", None)
        out.pop("protocol", None)
        if "username" in out:
            out["user"] = out.pop("username")
        return out


class WebdavFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'webdav4.fsspec.WebdavFileSystem'
    __orig_version__ = '0.10.0'
    protocol = ('webdav', 'dav')
    root_marker = ''
    sep = '/'

    @classmethod
    def _strip_protocol(cls, path: str) -> str:
        """Strips protocol from the given path, overriding for type-casting."""
        stripped = super()._strip_protocol(path)
        return cast(str, stripped)


class XRootDFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'fsspec_xrootd.xrootd.XRootDFileSystem'
    __orig_version__ = '0.5.1'
    protocol = ('root',)
    root_marker = '/'
    sep = '/'

    @classmethod
    def _strip_protocol(cls, path: str | list[str]) -> Any:
        if isinstance(path, str):
            if path.startswith(cls.protocol):
                x = urlsplit(path); return (x.path + f'?{x.query}' if x.query else '').rstrip("/") or cls.root_marker
            # assume already stripped
            return path.rstrip("/") or cls.root_marker
        elif isinstance(path, list):
            return [cls._strip_protocol(item) for item in path]
        else:
            raise ValueError("Strip protocol not given string or list")

    @staticmethod
    def _get_kwargs_from_urls(u: str) -> dict[Any, Any]:
        url = urlsplit(u)
        # The hostid encapsulates user,pass,host,port in one string
        return {"hostid": url.netloc}


class ZipFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'fsspec.implementations.zip.ZipFileSystem'
    __orig_version__ = '2025.3.2'
    protocol = ('zip',)
    root_marker = ''
    sep = '/'

    @classmethod
    def _strip_protocol(cls, path):
        # zip file paths are always relative to the archive root
        return super()._strip_protocol(path).lstrip("/")


class _DVCFileSystemFlavour(AbstractFileSystemFlavour):
    __orig_class__ = 'dvc.fs.dvc._DVCFileSystem'
    __orig_version__ = '3.59.1'
    protocol = ('dvc',)
    root_marker = '/'
    sep = '/'
