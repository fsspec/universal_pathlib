from typing import Dict, Type
import warnings

import upath
from upath.core import UPath


class _Registry:
    from upath.implementations import cloud, hdfs, http, memory, webdav

    known_implementations: Dict[str, Type[UPath]] = {
        "abfs": cloud.AzurePath,
        "adl": cloud.AzurePath,
        "az": cloud.AzurePath,
        "gcs": cloud.GCSPath,
        "gs": cloud.GCSPath,
        "hdfs": hdfs.HDFSPath,
        "http": http.HTTPPath,
        "https": http.HTTPPath,
        "memory": memory.MemoryPath,
        "s3": cloud.S3Path,
        "s3a": cloud.S3Path,
        "webdav+http": webdav.WebdavPath,
        "webdav+https": webdav.WebdavPath,
    }

    def __getitem__(self, item):
        implementation = self.known_implementations.get(item, None)
        if not implementation:
            warning_str = (
                f"{item} filesystem path not explicitly implemented. "
                "falling back to default implementation. "
                "This filesystem may not be tested"
            )
            warnings.warn(warning_str, UserWarning)
            return upath.UPath
        return implementation


_registry = _Registry()
