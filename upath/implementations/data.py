from __future__ import annotations

import sys
from collections.abc import Iterator
from collections.abc import Sequence
from typing import TYPE_CHECKING
from urllib.parse import quote_plus

from upath._protocol import get_upath_protocol
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
        try:
            (segment,) = pathsegments
        except ValueError:
            raise UnsupportedOperation("join not supported by DataPath")
        if get_upath_protocol(segment) != "data":
            raise ValueError(f"requires a data URI, got: {segment!r}")
        return type(self)(segment, protocol="data", **self.storage_options)

    @property
    def name(self) -> str:
        return quote_plus(self.path)

    @property
    def stem(self) -> str:
        return quote_plus(self.path)

    @property
    def suffix(self) -> str:
        return ""

    @property
    def suffixes(self) -> list[str]:
        return []

    def with_name(self, name: str) -> Self:
        raise UnsupportedOperation("with_name not supported by DataPath")

    def with_suffix(self, suffix: str) -> Self:
        raise UnsupportedOperation("with_suffix not supported by DataPath")

    def with_stem(self, stem: str) -> Self:
        raise UnsupportedOperation("with_stem not supported by DataPath")

    @property
    def parent(self) -> Self:
        return self

    @property
    def parents(self) -> Sequence[Self]:
        return []

    def full_match(self, pattern, *, case_sensitive: bool | None = None) -> bool:
        return super().full_match(pattern, case_sensitive=case_sensitive)

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

    def iterdir(self) -> Iterator[Self]:
        raise NotADirectoryError

    def glob(
        self, pattern, *, case_sensitive=None, recurse_symlinks=False
    ) -> Iterator[Self]:
        return iter([])

    def rglob(
        self, pattern, *, case_sensitive=None, recurse_symlinks=False
    ) -> Iterator[Self]:
        return iter([])

    def unlink(self, missing_ok: bool = False) -> None:
        raise UnsupportedOperation
