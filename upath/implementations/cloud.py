from __future__ import annotations

import re
import sys
import warnings
from typing import Any

import upath.core


class _CloudAccessor(upath.core._FSSpecAccessor):
    def _format_path(self, path):
        """
        netloc has already been set to project via `CloudPath._from_parts`
        """
        return f"{path._url.netloc}/{path._path.lstrip('/')}"

    def mkdir(self, path, create_parents=True, **kwargs):
        _path = self._format_path(path)
        if (
            not create_parents
            and not kwargs.get("exist_ok", False)
            and self._fs.exists(_path)
        ):
            raise FileExistsError(_path)
        return super().mkdir(path, create_parents=create_parents, **kwargs)


class CloudPath(upath.core.UPath):
    _default_accessor = _CloudAccessor

    @classmethod
    def _from_parts(cls, args, url=None, **kwargs):
        if kwargs.get("bucket") and url is not None:
            bucket = kwargs.pop("bucket")
            url = url._replace(netloc=bucket)
        obj = super()._from_parts(args, url, **kwargs)
        return obj

    @classmethod
    def _from_parsed_parts(cls, drv, root, parts, url=None, **kwargs):
        if kwargs.get("bucket") and url is not None:
            bucket = kwargs.pop("bucket")
            url = url._replace(netloc=bucket)
        obj = super()._from_parsed_parts(drv, root, parts, url=url, **kwargs)
        return obj

    def _sub_path(self, name):
        """
        `gcsfs` and `s3fs` return the full path as `<bucket>/<path>` with
        `listdir` and `glob`. However, in `iterdir` and `glob` we only want the
        relative path to `self`.
        """
        sp = re.escape(self._path)
        netloc = self._url.netloc
        return re.sub(
            f"^({netloc})?/?({sp}|{sp[1:]})/?",
            "",
            name,
        )

    def joinpath(self, *args):
        if self._url.netloc:
            return super().joinpath(*args)

        # if no bucket is defined for self
        sep = self._flavour.sep
        args_list = []
        for arg in args:
            if isinstance(arg, list):
                warnings.warn(
                    "lists as arguments to joinpath are deprecated",
                    DeprecationWarning,
                    stacklevel=2,
                )
                args_list.extend(arg)
            else:
                args_list.extend(arg.split(sep))
        bucket = args_list.pop(0)
        return type(self)(
            "/",
            *args_list,
            **self.storage_options,
            bucket=bucket,
            scheme=self.protocol,
        )

    @property
    def path(self) -> str:
        if self._url is None:
            raise RuntimeError(str(self))
        return f"{self._url.netloc}{super()._path}"


if sys.version_info >= (3, 12):
    from upath.core312plus import FSSpecFlavour

    class CloudPath(upath.core312plus.UPath):  # noqa
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
                args = [f"{self._protocol}://{bucket}/", *args]
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
