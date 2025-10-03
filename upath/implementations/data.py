from __future__ import annotations

import sys
from collections.abc import Sequence
from typing import TYPE_CHECKING

from upath.core import UPath
from upath.types import JoinablePathLike

if TYPE_CHECKING:
    if sys.version_info > (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self


class DataPath(UPath):

    @property
    def parts(self) -> Sequence[str]:
        return (self.path,)

    def __str__(self) -> str:
        return self.parser.join(*self._raw_urlpaths)

    def with_segments(self, *pathsegments: JoinablePathLike) -> Self:
        raise NotImplementedError("path operation not supported by DataPath")

    def with_suffix(self, suffix: str) -> Self:
        raise NotImplementedError("path operation not supported by DataPath")

    def mkdir(
        self, mode: int = 0o777, parents: bool = False, exist_ok: bool = False
    ) -> None:
        raise FileExistsError(str(self))

    def write_bytes(self, data: bytes) -> int:
        raise NotImplementedError("DataPath does not support writing")

    def write_text(
        self,
        data: str,
        encoding: str | None = ...,
        errors: str | None = ...,
        newline: str | None = ...,
    ) -> int:
        raise NotImplementedError("DataPath does not support writing")
