from __future__ import annotations

import sys
import warnings
from collections.abc import Iterator
from typing import TYPE_CHECKING
from typing import Any

from smbprotocol.exceptions import SMBOSError

from upath.core import UPath
from upath.types import UNSET_DEFAULT
from upath.types import WritablePathLike

if TYPE_CHECKING:
    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self


class SMBPath(UPath):
    __slots__ = ()

    def mkdir(
        self,
        mode: int = 0o777,
        parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
        # smbclient does not support setting mode externally
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
