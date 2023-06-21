from __future__ import annotations

import re

import upath.core


class _CloudAccessor(upath.core._FSSpecAccessor):
    def _format_path(self, path):
        """
        netloc has already been set to project via `CloudPath._from_parts`
        """
        return f"{path._url.netloc}/{path.path.lstrip('/')}"

    def mkdir(self, path, create_parents=True, **kwargs):
        _path = self._format_path(path)
        if (
            not create_parents
            and not kwargs.get("exist_ok", False)
            and self._fs.exists(_path)
        ):
            raise FileExistsError(_path)
        return super().mkdir(path, create_parents=create_parents, **kwargs)


# project is not part of the path, but is part of the credentials
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
        sp = re.escape(self.path)
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


class GCSPath(CloudPath):
    pass


class S3Path(CloudPath):
    pass


class AzurePath(CloudPath):
    pass
