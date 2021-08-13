import warnings

import upath


class _Registry:
    from upath.implementations import hdfs, http, memory, s3

    http = http.HTTPPath
    hdfs = hdfs.HDFSPath
    s3 = s3.S3Path
    memory = memory.MemoryPath

    def __getitem__(self, item):
        implemented_path = getattr(self, item, None)
        if not implemented_path:
            warning_str = (
                f"{item} filesystem path not explicitely implimented. "
                "falling back to default implimentation UniversalPath. "
                "This filesystem may not be tested"
            )
            warnings.warn(warning_str, UserWarning)
            return upath.UPath
        return implemented_path


_registry = _Registry()
