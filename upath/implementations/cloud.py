from __future__ import annotations

import posixpath
import re
import sys
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
        # handles a bucket in the path
        else:
            path = args[0]
            if isinstance(path, list):
                args_list = list(*args)
            else:
                args_list = path.split(self._flavour.sep)
            bucket = args_list.pop(0)
            self._kwargs["bucket"] = bucket
            return super().joinpath(*tuple(args_list))

    @property
    def path(self) -> str:
        if self._url is None:
            raise RuntimeError(str(self))
        return f"{self._url.netloc}{super()._path}"


if sys.version_info >= (3, 12):
    from upath.core312plus import PathOrStr
    from upath.core312plus import fsspecpathmod
    from upath.core312plus import split_upath_protocol
    from upath.core312plus import strip_upath_protocol

    class cloudpathmod(fsspecpathmod):
        sep: str = "/"
        altsep: str | None = None

        @staticmethod
        def join(__path: PathOrStr, *paths: PathOrStr) -> str:
            protocol = split_upath_protocol(__path)
            joined = posixpath.join(*map(strip_upath_protocol, [__path, *paths]))
            if protocol:
                return f"{protocol}://{joined}"
            else:
                return joined

        @staticmethod
        def splitroot(__path: PathOrStr) -> tuple[str, str, str]:
            protocol = split_upath_protocol(__path)
            path = strip_upath_protocol(__path)
            if protocol:
                drive, root, tail = path.partition("/")
                return drive, root or "/", tail
            else:
                return "", "", path

        @staticmethod
        def splitdrive(__path: PathOrStr) -> tuple[str, str]:
            protocol = split_upath_protocol(__path)
            path = strip_upath_protocol(__path)
            if protocol:
                drive, root, tail = path.partition("/")
                return drive, f"{root}{tail}"
            else:
                return "", path

    class CloudPath(upath.core.UPath):  # noqa
        pathmod = cloudpathmod

        def __init__(
            self, *args, protocol: str | None = None, **storage_options: Any
        ) -> None:
            if "bucket" in storage_options:
                bucket = storage_options.pop("bucket")
                args = [f"s3://{bucket}/", *args]
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


class GCSPath(CloudPath):
    pass


class S3Path(CloudPath):
    pass


class AzurePath(CloudPath):
    pass
