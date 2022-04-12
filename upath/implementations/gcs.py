import upath.core


# project is not part of the path, but is part of the credentials
class GCSPath(upath.core.UPath):
    @classmethod
    def _from_parts(cls, args, **kwargs):
        obj = super()._from_parts(args, **kwargs)
        if kwargs.get("bucket") and kwargs.get("_url"):
            bucket = obj._kwargs.pop("bucket")
            obj._url = obj._url._replace(netloc=bucket)
        return obj

    @classmethod
    def _from_parsed_parts(cls, drv, root, parts, **kwargs):
        obj = super()._from_parsed_parts(drv, root, parts, **kwargs)
        if kwargs.get("bucket") and kwargs.get("_url"):
            bucket = obj._kwargs.pop("bucket")
            obj._url = obj._url._replace(netloc=bucket)
        return obj
