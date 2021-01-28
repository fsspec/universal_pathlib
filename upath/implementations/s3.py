from upath.universal_path import _FSSpecAccessor, UniversalPath


class _S3Accessor(_FSSpecAccessor):
    def __init__(self, parsed_url, *args, **kwargs):
        super().__init__(parsed_url, *args, **kwargs)


class S3Path(UniversalPath):
    _default_accessor = _S3Accessor
