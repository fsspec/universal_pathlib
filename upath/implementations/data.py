from __future__ import annotations

import sys
from collections.abc import Sequence
from typing import TYPE_CHECKING

from upath.core import UnsupportedOperation
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
    from upath.types.storage_options import DataStorageOptions

__all__ = ["DataPath"]


class DataPath(UPath):
    __slots__ = ()

    if TYPE_CHECKING:

        def __init__(
            self,
            *args: JoinablePathLike,
            protocol: Literal["data"] | None = ...,
            chain_parser: FSSpecChainParser = ...,
            **storage_options: Unpack[DataStorageOptions],
        ) -> None: ...

    @property
    def parts(self) -> Sequence[str]:
        return (self.path,)

    def __str__(self) -> str:
        return self.parser.join(*self._raw_urlpaths)

    def with_segments(self, *pathsegments: JoinablePathLike) -> Self:
        raise UnsupportedOperation("path operation not supported by DataPath")

    def with_suffix(self, suffix: str) -> Self:
        raise UnsupportedOperation("path operation not supported by DataPath")

    def mkdir(
        self, mode: int = 0o777, parents: bool = False, exist_ok: bool = False
    ) -> None:
        raise FileExistsError(str(self))

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
