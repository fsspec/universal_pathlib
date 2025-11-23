from __future__ import annotations

import sys
from collections.abc import Iterator
from typing import TYPE_CHECKING
from typing import Any

from upath._chain import DEFAULT_CHAIN_PARSER
from upath._flavour import upath_strip_protocol
from upath.core import UPath
from upath.types import JoinablePathLike

if TYPE_CHECKING:
    from typing import Literal

    if sys.version_info >= (3, 11):
        from typing import Self
        from typing import Unpack
    else:
        from typing_extensions import Self
        from typing_extensions import Unpack

    from upath._chain import FSSpecChainParser
    from upath.types.storage_options import AzureStorageOptions
    from upath.types.storage_options import GCSStorageOptions
    from upath.types.storage_options import HfStorageOptions
    from upath.types.storage_options import S3StorageOptions

__all__ = [
    "CloudPath",
    "GCSPath",
    "S3Path",
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

    def mkdir(
        self, mode: int = 0o777, parents: bool = False, exist_ok: bool = False
    ) -> None:
        if not parents and not exist_ok and self.exists():
            raise FileExistsError(self.path)
        super().mkdir(mode=mode, parents=parents, exist_ok=exist_ok)

    def iterdir(self) -> Iterator[Self]:
        if self.is_file():
            raise NotADirectoryError(str(self))
        yield from super().iterdir()


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
