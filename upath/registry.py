import warnings

import upath


class _Registry:
    from upath.implementations import hdfs, http, memory, s3, gcs, azure

    http = http.HTTPPath
    hdfs = hdfs.HDFSPath
    s3a = s3.S3Path
    s3 = s3.S3Path
    memory = memory.MemoryPath
    gs = gcs.GCSPath
    gcs = gcs.GCSPath
    adl = azure.AzurePath
    az = azure.AzurePath
    abfs = azure.AzurePath

    def __getitem__(self, item):
        implemented_path = getattr(self, item, None)
        if not implemented_path:
            warning_str = (
                f"{item} filesystem path not explicitly implemented. "
                "falling back to default implementation. "
                "This filesystem may not be tested"
            )
            warnings.warn(warning_str, UserWarning)
            return upath.UPath
        return implemented_path


_registry = _Registry()
