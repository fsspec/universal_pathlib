from __future__ import annotations

import os
import sys
import warnings

if sys.version_info >= (3, 11):
    from typing import Self
    from typing import Unpack
else:
    from typing_extensions import Self
    from typing_extensions import Unpack

import smbprotocol.exceptions

from upath import UPath
from upath.core import _UPathRenameParams


class SMBPath(UPath):
    __slots__ = ()

    def mkdir(self, mode=0o777, parents=False, exist_ok=False):
        # smbclient does not support setting mode externally
        if parents and not exist_ok and self.exists():
            raise FileExistsError(str(self))
        try:
            self.fs.mkdir(
                self.path,
                create_parents=parents,
            )
        except smbprotocol.exceptions.SMBOSError:
            if not exist_ok:
                raise FileExistsError(str(self))
            if not self.is_dir():
                raise FileExistsError(str(self))

    def iterdir(self):
        if not self.is_dir():
            raise NotADirectoryError(str(self))
        else:
            return super().iterdir()

    def rename(
        self,
        target: str | os.PathLike[str] | UPath,
        **kwargs: Unpack[_UPathRenameParams],  # note: non-standard compared to pathlib
    ) -> Self:
        if kwargs.pop("recursive", None) is not None:
            warnings.warn(
                "SMBPath.rename(): recursive is currently ignored.",
                UserWarning,
                stacklevel=2,
            )
        if kwargs.pop("maxdepth", None) is not None:
            warnings.warn(
                "SMBPath.rename(): maxdepth is currently ignored.",
                UserWarning,
                stacklevel=2,
            )
        return super().rename(target, **kwargs)
