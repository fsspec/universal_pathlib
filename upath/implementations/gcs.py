from upath.universal_path import _FSSpecAccessor, UniversalPath


class _GCSAccessor(_FSSpecAccessor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class GCSPath(UniversalPath):
    _default_accessor = _GCSAccessor
