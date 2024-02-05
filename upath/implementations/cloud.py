from __future__ import annotations

from typing import Any

import upath.core
from upath._flavour import FSSpecFlavour


class CloudPath(upath.core.UPath):
    __slots__ = ()
    _flavour = FSSpecFlavour(
        join_prepends_protocol=True,
        supports_netloc=True,
    )

    def __init__(
        self, *args, protocol: str | None = None, **storage_options: Any
    ) -> None:
        if "bucket" in storage_options:
            bucket = storage_options.pop("bucket")
            args = (f"{self._protocol}://{bucket}/", *args)
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
