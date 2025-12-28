from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from upath.core import UnsupportedOperation
from upath.core import UPath
from upath.types import JoinablePathLike

if TYPE_CHECKING:
    from typing import Literal

    if sys.version_info >= (3, 11):
        from typing import Unpack
    else:
        from typing_extensions import Unpack

    from upath._chain import FSSpecChainParser
    from upath.types.storage_options import ZipStorageOptions


__all__ = ["ZipPath"]


class ZipPath(UPath):
    __slots__ = ()

    if TYPE_CHECKING:

        def __init__(
            self,
            *args: JoinablePathLike,
            protocol: Literal["zip"] | None = ...,
            chain_parser: FSSpecChainParser = ...,
            **storage_options: Unpack[ZipStorageOptions],
        ) -> None: ...

    @classmethod
    def _transform_init_args(cls, args, protocol, storage_options):
        if storage_options.get("mode") in {"a", "x", "w"}:
            raise UnsupportedOperation(
                "ZipPath write mode disabled in universal-pathlib"
            )
        return super()._transform_init_args(args, protocol, storage_options)

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
