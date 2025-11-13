from __future__ import annotations

import sys
import warnings
from collections.abc import Iterator
from itertools import chain
from typing import TYPE_CHECKING
from typing import Any
from urllib.parse import urlsplit

from fsspec.asyn import sync

from upath._stat import UPathStatResult
from upath.core import UPath
from upath.types import JoinablePathLike
from upath.types import StatResultType

if TYPE_CHECKING:
    from typing import Literal

    if sys.version_info >= (3, 11):
        from typing import Self
        from typing import Unpack
    else:
        from typing_extensions import Self
        from typing_extensions import Unpack

    from upath._chain import FSSpecChainParser
    from upath.types.storage_options import HTTPStorageOptions

__all__ = ["HTTPPath"]


class HTTPPath(UPath):
    __slots__ = ()

    if TYPE_CHECKING:

        def __init__(
            self,
            *args: JoinablePathLike,
            protocol: Literal["http", "https"] | None = ...,
            chain_parser: FSSpecChainParser = ...,
            **storage_options: Unpack[HTTPStorageOptions],
        ) -> None: ...

    @classmethod
    def _transform_init_args(
        cls,
        args: tuple[JoinablePathLike, ...],
        protocol: str,
        storage_options: dict[str, Any],
    ) -> tuple[tuple[JoinablePathLike, ...], str, dict[str, Any]]:
        # allow initialization via a path argument and protocol keyword
        if args and not str(args[0]).startswith(protocol):
            args = (f"{protocol}://{str(args[0]).lstrip('/')}", *args[1:])
        return args, protocol, storage_options

    def __str__(self) -> str:
        sr = urlsplit(super().__str__())
        return sr._replace(path=sr.path or "/").geturl()

    @property
    def path(self) -> str:
        sr = urlsplit(super().path)
        return sr._replace(path=sr.path or "/").geturl()

    def is_file(self, *, follow_symlinks: bool = True) -> bool:
        if not follow_symlinks:
            warnings.warn(
                f"{type(self).__name__}.is_file(follow_symlinks=False):"
                " is currently ignored.",
                UserWarning,
                stacklevel=2,
            )
        try:
            next(super().iterdir())
        except (StopIteration, NotADirectoryError):
            return True
        except FileNotFoundError:
            return False
        else:
            return False

    def is_dir(self, *, follow_symlinks: bool = True) -> bool:
        if not follow_symlinks:
            warnings.warn(
                f"{type(self).__name__}.is_dir(follow_symlinks=False):"
                " is currently ignored.",
                UserWarning,
                stacklevel=2,
            )
        try:
            next(super().iterdir())
        except (StopIteration, NotADirectoryError):
            return False
        except FileNotFoundError:
            return False
        else:
            return True

    def stat(self, follow_symlinks: bool = True) -> StatResultType:
        if not follow_symlinks:
            warnings.warn(
                f"{type(self).__name__}.stat(follow_symlinks=False):"
                " is currently ignored.",
                UserWarning,
                stacklevel=2,
            )
        info = self.fs.info(self.path)
        if "url" in info:
            info["type"] = "directory" if info["url"].endswith("/") else "file"
        return UPathStatResult.from_info(info)

    def iterdir(self) -> Iterator[Self]:
        it = iter(super().iterdir())
        try:
            item0 = next(it)
        except (StopIteration, NotADirectoryError):
            raise NotADirectoryError(str(self))
        except FileNotFoundError:
            raise FileNotFoundError(str(self))
        else:
            yield from chain([item0], it)

    def resolve(
        self,
        strict: bool = False,
        follow_redirects: bool = True,
    ) -> Self:
        """Normalize the path and resolve redirects."""
        # special handling of trailing slash behaviour
        parts = list(self.parts)
        if parts[-1:] == ["."]:
            parts[-1:] = [""]
        if parts[-2:] == ["", ".."]:
            parts[-2:] = [""]
        pth = self.with_segments(*parts)
        resolved_path = super(HTTPPath, pth).resolve(strict=strict)

        if follow_redirects:
            cls = type(self)
            # Get the fsspec fs
            fs = self.fs
            url = str(self)
            # Ensure we have a session
            session = sync(fs.loop, fs.set_session)
            # Use HEAD requests if the server allows it, falling back to GETs
            for method in (session.head, session.get):
                r = sync(fs.loop, method, url, allow_redirects=True)
                try:
                    r.raise_for_status()
                except Exception as exc:
                    if method == session.get:
                        raise FileNotFoundError(self) from exc
                else:
                    resolved_path = cls(str(r.url))
                    break

        return resolved_path
