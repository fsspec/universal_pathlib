from __future__ import annotations

import sys
from collections.abc import Iterator
from typing import TYPE_CHECKING
from typing import Any

from upath._flavour import upath_strip_protocol
from upath.core import UPath
from upath.types import JoinablePathLike

if TYPE_CHECKING:
    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self

__all__ = [
    "CloudPath",
    "GCSPath",
    "S3Path",
    "AzurePath",
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
        protocol: str | None = None,
        **storage_options: Any,
    ) -> None:
        super().__init__(*args, protocol=protocol, **storage_options)
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


class S3Path(CloudPath):
    __slots__ = ()

    def __init__(
        self,
        *args: JoinablePathLike,
        protocol: str | None = None,
        **storage_options: Any,
    ) -> None:
        super().__init__(*args, protocol=protocol, **storage_options)
        if not self.drive and len(self.parts) > 1:
            raise ValueError("non key-like path provided (bucket/container missing)")


class AzurePath(CloudPath):
    __slots__ = ()

    def __init__(
        self,
        *args: JoinablePathLike,
        protocol: str | None = None,
        **storage_options: Any,
    ) -> None:
        super().__init__(*args, protocol=protocol, **storage_options)
        if not self.drive and len(self.parts) > 1:
            raise ValueError("non key-like path provided (bucket/container missing)")
