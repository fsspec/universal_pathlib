import warnings

from upath.universal_path import UniversalPath
from upath.implementations import http, hdfs, s3, memory


class _Registry:
    http = http.HTTPPath
    hdfs = hdfs.HDFSPath
    s3 = s3.S3Path
    memory = memory.MemoryPath

    def __getitem__(self, item):
        implimented_path = getattr(self, item, None)
        if not implimented_path:
            warning_str = (
                f"{item} filesystem path not explicitely implimented. "
                "falling back to default implimentation UniversalPath. "
                "This filesystem may not be tested"
            )
            warnings.warn(warning_str, UserWarning)
            return UniversalPath
        return implimented_path


_registry = _Registry()
