from .. import core
import os
import re


class _AzureAccessor(core._FSSpecAccessor):
    def __init__(self, parsed_url, *args, **kwargs):
        super().__init__(parsed_url, *args, **kwargs)

    def _format_path(self, s):
        """If the filesystem backend doesn't have a root_marker, strip the
        leading slash of a path and add the bucket
        """
        return os.path.join(self._url.netloc, s.lstrip("/"))


class AzurePath(core.UPath):
    _default_accessor = _AzureAccessor

    def _init(self, *args, template=None, **kwargs):
        if kwargs.get("storage_options"):
            kwargs.update(kwargs["storage_options"])
        super()._init(*args, template=template, **kwargs)

    def _sub_path(self, name):
        sp = self.path
        return re.sub(f"^({self._url.netloc})?/?({sp}|{sp[1:]})/?", "", name)
