from __future__ import annotations

from upath.core import UPath


class DataPath(UPath):

    @property
    def parts(self):
        return (self.path,)

    def __str__(self):
        return self.parser.join(*self._raw_urlpaths)

    def with_segments(self, *pathsegments):
        raise NotImplementedError("path operation not supported by DataPath")

    def with_suffix(self, suffix: str):
        raise NotImplementedError("path operation not supported by DataPath")

    def mkdir(self, mode=0o777, parents=False, exist_ok=False):
        raise FileExistsError(str(self))

    def write_bytes(self, data):
        raise NotImplementedError("DataPath does not support writing")

    def write_text(self, data, **kwargs):
        raise NotImplementedError("DataPath does not support writing")
