from __future__ import annotations

import sys
import warnings
from collections.abc import Iterator
from typing import TYPE_CHECKING
from typing import Any

from upath.core import UPath
from upath.types import UNSET_DEFAULT
from upath.types import JoinablePathLike
from upath.types import WritablePathLike

if TYPE_CHECKING:
    from typing import Literal

    if sys.version_info >= (3, 11):
        from typing import Self
        from typing import Unpack
    else:
        from typing_extensions import Self
        from typing_extensions import Unpack

    from upath._chain import FSSpecChainParser
    from upath.types.storage_options import SMBStorageOptions


class SMBPath(UPath):
    __slots__ = ()

    if TYPE_CHECKING:

        def __init__(
            self,
            *args: JoinablePathLike,
            protocol: Literal["smb"] | None = ...,
            chain_parser: FSSpecChainParser = ...,
            **storage_options: Unpack[SMBStorageOptions],
        ) -> None: ...

    @property
    def path(self) -> str:
        path = super().path
        if len(path) > 1:
            return path.removesuffix("/")
        return path

    def __str__(self) -> str:
        path_str = super().__str__()
        if path_str.startswith("smb:///"):
            return path_str.removesuffix("/")
        return path_str

    def mkdir(
        self,
        mode: int = 0o777,
        parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
        # smbclient does not support setting mode externally
        from smbprotocol.exceptions import SMBOSError

        if parents and not exist_ok and self.exists():
            raise FileExistsError(str(self))
        try:
            self.fs.mkdir(
                self.path,
                create_parents=parents,
            )
        except SMBOSError:
            if not exist_ok:
                raise FileExistsError(str(self))
            if not self.is_dir():
                raise FileExistsError(str(self))

    def iterdir(self) -> Iterator[Self]:
        if not self.is_dir():
            raise NotADirectoryError(str(self))
        else:
            return super().iterdir()

    def rename(
        self,
        target: WritablePathLike,
        *,
        recursive: bool = UNSET_DEFAULT,
        maxdepth: int | None = UNSET_DEFAULT,
        **kwargs: Any,
    ) -> Self:
        if recursive is not UNSET_DEFAULT:
            warnings.warn(
                "SMBPath.rename(): recursive is currently ignored.",
                UserWarning,
                stacklevel=2,
            )
        if maxdepth is not UNSET_DEFAULT:
            warnings.warn(
                "SMBPath.rename(): maxdepth is currently ignored.",
                UserWarning,
                stacklevel=2,
            )
        return super().rename(target, **kwargs)
