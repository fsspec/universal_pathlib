from __future__ import annotations

import upath.core


class _DataAccessor(upath.core._FSSpecAccessor):

    def _format_path(self, path):
        return str(path)

class DataPath(upath.core.UPath):
    _default_accessor = _DataAccessor

