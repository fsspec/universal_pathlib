from __future__ import annotations

from typing import Any

from upath._compat import FSSpecAccessorShim as _FSSpecAccessorShim
from upath._flavour import FSSpecFlavour as _FSSpecFlavour
from upath.core import UPath

__all__ = [
    "CloudPath",
    "GCSPath",
    "S3Path",
    "AzurePath",
]


# accessors are deprecated
_CloudAccessor = _FSSpecAccessorShim


class CloudPath(UPath):
    __slots__ = ()
    _flavour = _FSSpecFlavour(
        join_prepends_protocol=True,
        supports_netloc=True,
    )

    def __init__(
        self, *args, protocol: str | None = None, **storage_options: Any
    ) -> None:
        for key in ["bucket", "netloc"]:
            bucket = storage_options.pop(key, None)
            if bucket:
                if args[0].startswith("/"):
                    args = (f"{self._protocol}://{bucket}{args[0]}", *args[1:])
                else:
                    args = (f"{self._protocol}://{bucket}/", *args)
                break
        super().__init__(*args, protocol=protocol, **storage_options)

    def mkdir(
        self, mode: int = 0o777, parents: bool = False, exist_ok: bool = False
    ) -> None:
        if not parents and not exist_ok and self.exists():
            raise FileExistsError(self.path)
        super().mkdir(mode=mode, parents=parents, exist_ok=exist_ok)

    def iterdir(self):
        if self.is_file():
            raise NotADirectoryError(str(self))
        yield from super().iterdir()

    def relative_to(self, other, /, *_deprecated, walk_up=False):
        # use the parent implementation for the ValueError logic
        super().relative_to(other, *_deprecated, walk_up=False)
        return self


class GCSPath(CloudPath):
    __slots__ = ()

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


class AzurePath(CloudPath):
    __slots__ = ()

    def touch(self, mode=0o666, exist_ok=True):
        if exist_ok and self.exists():
            with self.fs.open(self.path, mode="a"):
                pass
        else:
            self.fs.touch(self.path, truncate=True)
