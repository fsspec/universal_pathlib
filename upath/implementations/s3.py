import os
import re

from upath.universal_path import _FSSpecAccessor, UniversalPath


class _S3Accessor(_FSSpecAccessor):
    def __init__(self, parsed_url, *args, **kwargs):
        super().__init__(parsed_url, *args, **kwargs)

    def _format_path(self, s):
        s = os.path.join(self._url.netloc, s.lstrip("/"))
        return s


class S3Path(UniversalPath):
    _default_accessor = _S3Accessor

    def _sub_path(self, name):
        """s3fs returns path as `{bucket}/<path>` with listdir
        and glob, so here we can add the netloc to the sub string
        so it gets subbed out as well
        """
        sp = self.path
        return re.sub(f"^{self._url.netloc}/({sp}|{sp[1:]})/", "", name)
