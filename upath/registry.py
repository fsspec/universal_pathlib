from typing import Dict, Type
import warnings

import upath
from upath.core import UPath


class _Registry:
    from upath.implementations import hdfs, http, memory, s3, gcs

    known_implementations: Dict[str, Type[UPath]] = {
        "https": http.HTTPPath,
        "http": http.HTTPPath,
        "hdfs": hdfs.HDFSPath,
        "s3a": s3.S3Path,
        "s3": s3.S3Path,
        "memory": memory.MemoryPath,
        "gs": gcs.GCSPath,
        "gcs": gcs.GCSPath,
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
