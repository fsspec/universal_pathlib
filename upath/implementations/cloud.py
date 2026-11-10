from __future__ import annotations

import sys
from collections.abc import Iterator
from collections.abc import Sequence
from typing import TYPE_CHECKING
from typing import Any
from typing import overload
from urllib.parse import urlsplit

from fsspec.registry import get_filesystem_class

from upath import UnsupportedOperation
from upath._chain import DEFAULT_CHAIN_PARSER
from upath._flavour import upath_strip_protocol
from upath.core import UPath
from upath.types import JoinablePathLike
from upath.types import SupportsPathLike
from upath.types import WritablePath

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Literal
    from typing import TypeVar

    if sys.version_info >= (3, 11):
        from typing import Self
        from typing import Unpack
    else:
        from typing_extensions import Self
        from typing_extensions import Unpack

    from fsspec import AbstractFileSystem

    from upath._chain import FSSpecChainParser
    from upath.types.storage_options import AzureStorageOptions
    from upath.types.storage_options import GCSStorageOptions
    from upath.types.storage_options import HfStorageOptions
    from upath.types.storage_options import S3StorageOptions

    _WT = TypeVar("_WT", bound="WritablePath")

__all__ = [
    "CloudPath",
    "GCSPath",
    "S3Path",
    "S3HttpPath",
    "AzurePath",
    "HfPath",
]


class CloudPath(UPath):
    __slots__ = ()

    @classmethod
    def _transform_init_args(
        cls,
        args: tuple[JoinablePathLike, ...],
        protocol: str,
        storage_options: dict[str, Any],
    ) -> tuple[tuple[JoinablePathLike, ...], str, dict[str, Any]]:
        for key in ["bucket", "netloc"]:
            bucket = storage_options.pop(key, None)
            if bucket:
                if str(args[0]).startswith("/"):
                    args = (f"{protocol}://{bucket}{args[0]}", *args[1:])
                else:
                    args0 = upath_strip_protocol(args[0])
                    args = (f"{protocol}://{bucket}/", args0, *args[1:])
                break
        return super()._transform_init_args(args, protocol, storage_options)

    @property
    def root(self) -> str:
        if self._relative_base is not None:
            return ""
        return self.parser.sep

    def __str__(self) -> str:
        path = super().__str__()
        if self._relative_base is None:
            drive = self.parser.splitdrive(path)[0]
            if drive and path == f"{self.protocol}://{drive}":
                return f"{path}{self.root}"
        return path

    @property
    def path(self) -> str:
        self_path = super().path.rstrip(self.parser.sep)
        if (
            self._relative_base is None
            and self_path
            and self.parser.sep not in self_path
        ):
            return self_path + self.root
        return self_path

    @property
    def parts(self) -> Sequence[str]:
        parts = super().parts
        if self._relative_base is None and len(parts) == 2 and not parts[1]:
            return parts[:1]
        return parts

    def mkdir(
        self, mode: int = 0o777, parents: bool = False, exist_ok: bool = False
    ) -> None:
        if not parents and not exist_ok and self.exists():
            raise FileExistsError(self.path)
        super().mkdir(mode=mode, parents=parents, exist_ok=exist_ok)


class GCSPath(CloudPath):
    __slots__ = ()

    def __init__(
        self,
        *args: JoinablePathLike,
        protocol: Literal["gcs", "gs"] | None = None,
        chain_parser: FSSpecChainParser = DEFAULT_CHAIN_PARSER,
        **storage_options: Unpack[GCSStorageOptions],
    ) -> None:
        super().__init__(
            *args, protocol=protocol, chain_parser=chain_parser, **storage_options
        )
        if not self.drive and len(self.parts) > 1:
            raise ValueError("non key-like path provided (bucket/container missing)")

    def mkdir(
        self, mode: int = 0o777, parents: bool = False, exist_ok: bool = False
    ) -> None:
        try:
            super().mkdir(mode=mode, parents=parents, exist_ok=exist_ok)
        except TypeError as err:
            if "unexpected keyword argument 'create_parents'" in str(err):
                self.fs.mkdir(self.path)

    def exists(self, *, follow_symlinks: bool = True) -> bool:
        # required for gcsfs<2025.5.0, see: https://github.com/fsspec/gcsfs/pull/676
        path = self.path
        if len(path) > 1:
            path = path.removesuffix(self.root)
        return self.fs.exists(path)


class S3Path(CloudPath):
    __slots__ = ()

    def __init__(
        self,
        *args: JoinablePathLike,
        protocol: Literal["s3", "s3a"] | None = None,
        chain_parser: FSSpecChainParser = DEFAULT_CHAIN_PARSER,
        **storage_options: Unpack[S3StorageOptions],
    ) -> None:
        super().__init__(
            *args, protocol=protocol, chain_parser=chain_parser, **storage_options
        )
        if not self.drive and len(self.parts) > 1:
            raise ValueError("non key-like path provided (bucket/container missing)")

    @overload
    def copy(self, target: _WT, **kwargs: Any) -> _WT: ...

    @overload
    def copy(self, target: SupportsPathLike | str, **kwargs: Any) -> Self: ...

    def copy(self, target: _WT | SupportsPathLike | str, **kwargs: Any) -> _WT | UPath:
        """
        Recursively copy this file or directory tree to the given destination.
        """
        # to allow _copy_from to check if a path isfile AND isdir
        # we need to disable s3fs's dircache mechanism because it
        # currently implements a XOR relation the two for objects
        # ref: fsspec/s3fs#999
        sopts = dict(self.storage_options)
        sopts["use_listings_cache"] = False
        new_self = type(self)(
            self.path,
            protocol=self.protocol,  # type: ignore
            **sopts,
        )
        assert type(self) is type(new_self)
        return super(S3Path, new_self).copy(target, **kwargs)


class S3HttpPath(S3Path):
    """S3 compatible storage at an explicit endpoint

    Supports `s3+http://endpoint/bucket/key` and `s3+https://endpoint/bucket/key`
    urls as defined in https://github.com/jbms/url-pipeline. The endpoint is
    stored in the `endpoint_url` storage option and the first path segment is
    always interpreted as the bucket.
    """

    __slots__ = ()

    def __init__(
        self,
        *args: JoinablePathLike,
        protocol: Literal["s3+http", "s3+https"] | None = None,
        chain_parser: FSSpecChainParser = DEFAULT_CHAIN_PARSER,
        **storage_options: Unpack[S3StorageOptions],
    ) -> None:
        super().__init__(
            *args,
            protocol=protocol,  # type: ignore[arg-type]
            chain_parser=chain_parser,
            **storage_options,
        )
        endpoint_url = self.storage_options.get("endpoint_url")
        if not endpoint_url:
            raise ValueError(
                f"must provide `endpoint_url` storage option for args: {args!r}"
            )
        url = urlsplit(endpoint_url)
        if (
            f"s3+{url.scheme}" != self.protocol
            or not url.netloc
            or url.path.strip("/")
            or url.query
            or url.fragment
        ):
            raise ValueError(
                f"endpoint_url={endpoint_url!r} can't be expressed"
                f" as a {self.protocol!r} url"
            )

    @classmethod
    def _parse_storage_options(
        cls,
        urlpath: str,
        protocol: str,
        storage_options: Mapping[str, Any],
    ) -> dict[str, Any]:
        so = super()._parse_storage_options(urlpath, protocol, storage_options)
        if urlpath.startswith(("s3+http://", "s3+https://")):
            url = urlsplit(urlpath)
            url_endpoint = f"{url.scheme.partition('+')[2]}://{url.netloc}"
            endpoint_url = so.setdefault("endpoint_url", url_endpoint)
            if endpoint_url.rstrip("/") != url_endpoint:
                raise ValueError(
                    f"endpoint_url={endpoint_url!r} conflicts with"
                    f" endpoint in url {urlpath!r}"
                )
        return so

    @classmethod
    def _fs_factory(
        cls,
        urlpath: str,
        protocol: str,
        storage_options: Mapping[str, Any],
    ) -> AbstractFileSystem:
        fs_cls = get_filesystem_class("s3")
        return fs_cls(**storage_options)

    def __str__(self) -> str:
        endpoint_url = self.storage_options.get("endpoint_url")
        if self._relative_base is not None or not endpoint_url:
            return super().__str__()
        netloc = urlsplit(endpoint_url).netloc
        return f"{self.protocol}://{netloc}/{self.path}"


class AzurePath(CloudPath):
    __slots__ = ()

    def __init__(
        self,
        *args: JoinablePathLike,
        protocol: Literal["abfs", "abfss", "adl", "az"] | None = None,
        chain_parser: FSSpecChainParser = DEFAULT_CHAIN_PARSER,
        **storage_options: Unpack[AzureStorageOptions],
    ) -> None:
        super().__init__(
            *args, protocol=protocol, chain_parser=chain_parser, **storage_options
        )
        if not self.drive and len(self.parts) > 1:
            raise ValueError("non key-like path provided (bucket/container missing)")


class HfPath(CloudPath):
    __slots__ = ()

    def __init__(
        self,
        *args: JoinablePathLike,
        protocol: Literal["hf"] | None = None,
        chain_parser: FSSpecChainParser = DEFAULT_CHAIN_PARSER,
        **storage_options: Unpack[HfStorageOptions],
    ) -> None:
        super().__init__(
            *args, protocol=protocol, chain_parser=chain_parser, **storage_options
        )

    @property
    def root(self) -> str:
        return ""

    def iterdir(self) -> Iterator[Self]:
        try:
            yield from super().iterdir()
        except (NotImplementedError, ValueError):
            # listing a namespace (e.g. a user's repositories) is unsupported:
            # older huggingface_hub raises NotImplementedError, newer versions
            # reject the single-segment repository id with a ValueError
            raise UnsupportedOperation

    def touch(self, mode: int = 0o666, exist_ok: bool = True) -> None:
        raise UnsupportedOperation

    def mkdir(
        self,
        mode: int = 0o777,
        parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
        raise UnsupportedOperation

    def unlink(self, missing_ok: bool = False) -> None:
        raise UnsupportedOperation

    def write_bytes(self, data: bytes) -> int:
        raise UnsupportedOperation("DataPath does not support writing")

    def write_text(
        self,
        data: str,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> int:
        raise UnsupportedOperation("DataPath does not support writing")
