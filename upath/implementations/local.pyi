from pathlib import PosixPath
from pathlib import WindowsPath

from upath.core import UPath

class LocalPath(UPath): ...
class FilePath(LocalPath): ...

class PosixUPath(PosixPath, LocalPath):  # type: ignore[misc]
    ...

class WindowsUPath(WindowsPath, LocalPath):  # type: ignore[misc]
    ...
