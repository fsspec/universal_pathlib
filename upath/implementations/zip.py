from __future__ import annotations

import sys
from typing import TYPE_CHECKING
from zipfile import ZipInfo

from upath.core import UPath
from upath.types import JoinablePathLike

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Literal

    if sys.version_info >= (3, 11):
        from typing import Self
        from typing import Unpack
    else:
        from typing_extensions import Self
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

    def iterdir(self) -> Iterator[Self]:
        if self.is_file():
            raise NotADirectoryError(str(self))
        yield from super().iterdir()

    if sys.version_info >= (3, 11):

        def mkdir(
            self,
            mode: int = 0o777,
            parents: bool = False,
            exist_ok: bool = False,
        ) -> None:
            is_dir = self.is_dir()
            if is_dir and not exist_ok:
                raise FileExistsError(f"File exists: {self.path!r}")
            elif not is_dir:
                zipfile = self.fs.zip
                zipfile.mkdir(self.path, mode)

    else:

        def mkdir(
            self,
            mode: int = 0o777,
            parents: bool = False,
            exist_ok: bool = False,
        ) -> None:
            is_dir = self.is_dir()
            if is_dir and not exist_ok:
                raise FileExistsError(f"File exists: {self.path!r}")
            elif not is_dir:
                dirname = self.path
                if dirname and not dirname.endswith("/"):
                    dirname += "/"
                zipfile = self.fs.zip
                zinfo = ZipInfo(dirname)
                zinfo.compress_size = 0
                zinfo.CRC = 0
                zinfo.external_attr = ((0o40000 | mode) & 0xFFFF) << 16
                zinfo.file_size = 0
                zinfo.external_attr |= 0x10
                zipfile.writestr(zinfo, b"")
